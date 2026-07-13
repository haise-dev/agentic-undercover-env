from datetime import UTC, datetime

from src.engine.context_builder import ContextBuilder
from src.engine.event_emitter import (
    EVT_AGENT_DELIBERATED,
    EventEmitter,
)
from src.engine.exceptions import AgentOutputError, RateLimitError
from src.models import DeliberationOutput, Phase, PublicMessage

_MAX_DELIBERATE_ATTEMPTS = 2


async def deliberation_node(
    state: dict | object,
    agents: dict,
    emitter: EventEmitter,
) -> dict | object:
    """
    Runs a single turn in the Deliberation Phase for the agent specified in game_state.next_speaker_id.

    Args:
        state: LangGraph GraphState (dict) or GameState.
        agents: Dictionary of agent_id -> AIAgent.
        emitter: Redis EventEmitter.

    Returns:
        GraphState (dict) or GameState containing the mutated GameState.

    Raises:
        ValueError: If next_speaker_id is not set.
        AgentOutputError: If the agent fails to produce a valid response.
    """
    is_graph_state = isinstance(state, dict) and "game_state" in state
    game_state = state["game_state"] if is_graph_state else state

    # Detect first entry into this deliberation segment
    if game_state.current_phase != Phase.DELIBERATION:
        saved_speaker = game_state.next_speaker_id
        game_state.reset_deliberation_tracking()
        game_state.next_speaker_id = saved_speaker
        game_state.current_phase = Phase.DELIBERATION

    agent_id = game_state.next_speaker_id
    if agent_id is None:
        raise ValueError(
            "deliberation_node called with next_speaker_id=None. "
            "The router must set next_speaker_id before routing here."
        )

    context = ContextBuilder.build(game_state, agent_id)
    agent = agents[agent_id]

    output = await _deliberate_with_retry(
        agent=agent,
        context=context,
        agent_id=agent_id,
        episode_id=game_state.episode_id,
    )

    # Build PublicMessage for deliberation
    agent_config = next(a for a in game_state.config.agents if a.agent_id == agent_id)
    message = PublicMessage(
        agent_id=agent_id,
        display_name=agent_config.display_name,
        phase=Phase.DELIBERATION,
        round_number=game_state.current_round,
        deliberation_round=game_state.current_deliberation_round,
        content=output.public_statement,
        timestamp=datetime.now(UTC).isoformat(),
    )

    # Append to GameState immediately for next agents to see
    game_state.all_messages.append(message)

    # Update tracking fields
    game_state.deliberation_message_count += 1
    game_state.turns_count[agent_id] = game_state.turns_count.get(agent_id, 0) + 1
    game_state.speakers_this_round.add(agent_id)
    game_state.next_speaker_id = None  # Clear it so the router can set it again

    # Emit Redis Event with intent details
    await emitter.emit(
        EVT_AGENT_DELIBERATED,
        {
            "agent_id": agent_id,
            "display_name": agent_config.display_name,
            "public_statement": output.public_statement,
            "intent": output.intent,
            "target_name": output.target_name,
            "phase": Phase.DELIBERATION,
            "round_number": game_state.current_round,
            "deliberation_round": game_state.current_deliberation_round,
        },
    )

    return state


async def _deliberate_with_retry(
    agent,
    context,
    agent_id: str,
    episode_id: str,
) -> DeliberationOutput:
    """
    Invokes agent.deliberate() with retries.
    Raises AgentOutputError on exhaustion.
    """
    last_exc: Exception | None = None
    for attempt in range(_MAX_DELIBERATE_ATTEMPTS):
        try:
            output = await agent.deliberate(context)
            if _is_valid_deliberation_output(output):
                return output
            last_exc = ValueError(
                f"Agent '{agent_id}' produced invalid DeliberationOutput "
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
            f"Agent '{agent_id}' failed to produce valid DeliberationOutput "
            f"after {_MAX_DELIBERATE_ATTEMPTS} attempts. Last error: {last_exc}"
        ),
        agent_id=agent_id,
        phase="deliberation",
        episode_id=episode_id,
    )


def _is_valid_deliberation_output(output: object) -> bool:
    """Checks if the output matches the required DeliberationOutput format."""
    return (
        isinstance(output, DeliberationOutput)
        and bool(output.inner_thought.strip())
        and bool(output.public_statement.strip())
    )
