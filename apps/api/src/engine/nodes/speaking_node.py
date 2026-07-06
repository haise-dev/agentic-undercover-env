import random
from datetime import UTC, datetime

from src.engine.context_builder import ContextBuilder
from src.engine.event_emitter import (
    EVT_AGENT_SPOKE,
    EVT_ROUND_STARTED,
    EventEmitter,
)
from src.engine.exceptions import AgentOutputError, RateLimitError
from src.models import (
    GameState,
    Phase,
    PublicMessage,
    SpeakingOutput,
    SystemAnnouncement,
)

_MAX_SPEAK_ATTEMPTS = 2


async def speaking_node(
    state: dict | GameState,
    agents: dict,
    emitter: EventEmitter,
    is_final_round: bool | None = None,
) -> dict | GameState:
    """
    Runs one full speaking round.

    Agents speak sequentially in state.current_turn_order.
    Each agent's context includes all messages emitted by earlier agents
    this round.

    Args:
        state:          Current GraphState (dict) or GameState.
        agents:         Mapping of agent_id → agent instance.
        emitter:        EventEmitter connected to this episode's Redis channel.
        is_final_round: Whether this is the last allowed round.
                        If None, computed automatically from max_rounds.

    Returns:
        Mutated GraphState or GameState with all agents' PublicMessages appended.

    Raises:
        AgentOutputError: if any agent fails to produce valid SpeakingOutput
                          after 2 total attempts.
        ValueError:       if state.current_phase is not INIT, SPEAKING, or POLLING.
    """
    is_graph_state = isinstance(state, dict) and "game_state" in state
    game_state = state["game_state"] if is_graph_state else state

    if game_state.current_phase not in (Phase.INIT, Phase.SPEAKING, Phase.POLLING):
        raise ValueError(
            f"speaking_node requires Phase.INIT, Phase.SPEAKING, or Phase.POLLING, got {game_state.current_phase}"
        )

    is_loopback = game_state.current_phase == Phase.POLLING

    if is_loopback:
        # Increment round number
        game_state.current_round += 1

        # Reset turn order to a new random permutation of alive agents
        alive_ids = [aid for aid, alive in game_state.agent_alive.items() if alive]
        random.shuffle(alive_ids)
        game_state.current_turn_order = alive_ids

        # Inject system announcement
        game_state.all_announcements.append(
            SystemAnnouncement(
                phase=Phase.SPEAKING,
                round_number=game_state.current_round,
                content=f"Round {game_state.current_round} begins. No vote was called in the previous round.",
                timestamp=datetime.now(UTC).isoformat(),
            )
        )

    game_state.current_phase = Phase.SPEAKING

    if is_final_round is None:
        is_final_round = game_state.current_round >= game_state.config.max_rounds

    # Emit round started
    await emitter.emit(
        EVT_ROUND_STARTED,
        {
            "episode_id": game_state.episode_id,
            "round_number": game_state.current_round,
            "turn_order": game_state.current_turn_order,
        },
    )

    # Sequential speaking loop
    for agent_id in game_state.current_turn_order:
        context = ContextBuilder.build(game_state, agent_id, is_final_round)
        agent = agents[agent_id]

        output = await _speak_with_retry(
            agent=agent,
            context=context,
            agent_id=agent_id,
            episode_id=game_state.episode_id,
        )

        # Build PublicMessage
        agent_config = next(
            a for a in game_state.config.agents if a.agent_id == agent_id
        )
        message = PublicMessage(
            agent_id=agent_id,
            display_name=agent_config.display_name,
            phase=Phase.SPEAKING,
            round_number=game_state.current_round,
            deliberation_round=None,
            content=output.public_statement,
            timestamp=datetime.now(UTC).isoformat(),
        )

        # Append to GameState immediately — next agent sees this message
        game_state.all_messages.append(message)

        # Emit AGENT_SPOKE
        await emitter.emit(
            EVT_AGENT_SPOKE,
            {
                "agent_id": agent_id,
                "display_name": agent_config.display_name,
                "public_statement": output.public_statement,
                "phase": Phase.SPEAKING,
                "round_number": game_state.current_round,
            },
        )

    return state


async def _speak_with_retry(
    agent,
    context,
    agent_id: str,
    episode_id: str,
) -> SpeakingOutput:
    """
    Calls agent.speak() with up to _MAX_SPEAK_ATTEMPTS total attempts.
    Raises AgentOutputError if all attempts fail.
    """
    last_exc: Exception | None = None
    for attempt in range(_MAX_SPEAK_ATTEMPTS):
        try:
            output = await agent.speak(context)
            if _is_valid_speaking_output(output):
                return output
            last_exc = ValueError(
                f"Agent '{agent_id}' produced invalid SpeakingOutput "
                f"on attempt {attempt + 1}: "
                f"inner_thought={repr(output.inner_thought)!r}, "
                f"public_statement={repr(output.public_statement)!r}"
            )
        except RateLimitError:
            raise
        except Exception as exc:
            last_exc = exc

    raise AgentOutputError(
        message=(
            f"Agent '{agent_id}' failed to produce valid SpeakingOutput "
            f"after {_MAX_SPEAK_ATTEMPTS} attempts. Last error: {last_exc}"
        ),
        agent_id=agent_id,
        phase="speaking",
        episode_id=episode_id,
    )


def _is_valid_speaking_output(output: object) -> bool:
    """Returns True if output is a SpeakingOutput with non-empty fields."""
    return (
        isinstance(output, SpeakingOutput)
        and bool(output.inner_thought.strip())
        and bool(output.public_statement.strip())
    )
