from datetime import UTC, datetime

from src.engine.context_builder import ContextBuilder
from src.engine.event_emitter import (
    EVT_AGENT_SPOKE,
    EVT_ROUND_STARTED,
    EventEmitter,
)
from src.engine.exceptions import AgentOutputError
from src.models import GameState, Phase, PublicMessage, SpeakingOutput

_MAX_SPEAK_ATTEMPTS = 2


async def speaking_node(
    state: GameState,
    agents: dict,
    emitter: EventEmitter,
    is_final_round: bool = False,
) -> GameState:
    """
    Runs one full speaking round.

    Agents speak sequentially in state.current_turn_order.
    Each agent's context includes all messages emitted by earlier agents
    this round.

    Args:
        state:          Current GameState. Must have current_phase == Phase.SPEAKING.
        agents:         Mapping of agent_id → agent instance.
        emitter:        EventEmitter connected to this episode's Redis channel.
        is_final_round: Whether this is the last allowed round.
                        Passed to ContextBuilder for prompt injection.

    Returns:
        Mutated GameState with all agents' PublicMessages appended.

    Raises:
        AgentOutputError: if any agent fails to produce valid SpeakingOutput
                          after 2 total attempts.
        ValueError:       if state.current_phase != Phase.SPEAKING.
    """
    if state.current_phase != Phase.SPEAKING:
        raise ValueError(
            f"speaking_node requires Phase.SPEAKING, got {state.current_phase}"
        )

    # Emit round started
    await emitter.emit(
        EVT_ROUND_STARTED,
        {
            "episode_id": state.episode_id,
            "round_number": state.current_round,
            "turn_order": state.current_turn_order,
        },
    )

    # Sequential speaking loop
    for agent_id in state.current_turn_order:
        context = ContextBuilder.build(state, agent_id, is_final_round)
        agent = agents[agent_id]

        output = await _speak_with_retry(
            agent=agent,
            context=context,
            agent_id=agent_id,
            episode_id=state.episode_id,
        )

        # Build PublicMessage
        agent_config = next(a for a in state.config.agents if a.agent_id == agent_id)
        message = PublicMessage(
            agent_id=agent_id,
            display_name=agent_config.display_name,
            phase=Phase.SPEAKING,
            round_number=state.current_round,
            deliberation_round=None,
            content=output.public_statement,
            timestamp=datetime.now(UTC).isoformat(),
        )

        # Append to GameState immediately — next agent sees this message
        state.all_messages.append(message)

        # Emit AGENT_SPOKE
        await emitter.emit(
            EVT_AGENT_SPOKE,
            {
                "agent_id": agent_id,
                "display_name": agent_config.display_name,
                "public_statement": output.public_statement,
                "phase": Phase.SPEAKING,
                "round_number": state.current_round,
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
