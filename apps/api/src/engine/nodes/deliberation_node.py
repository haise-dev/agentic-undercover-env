import random
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
    Runs the Deliberation Phase: 2 full rounds of sequential deliberation.

    At each sub-round:
    - Randomizes the speaking order of all alive agents.
    - Each alive agent delivers a deliberation statement based on current context.
    - Appends deliberation statements to GameState and emits events.

    Args:
        state: LangGraph GraphState (dict) or GameState.
        agents: Dictionary of agent_id -> AIAgent.
        emitter: Redis EventEmitter.

    Returns:
        GraphState (dict) or GameState containing the mutated GameState.

    Raises:
        AgentOutputError: If an agent fails to produce a valid response.
    """
    is_graph_state = isinstance(state, dict) and "game_state" in state
    game_state = state["game_state"] if is_graph_state else state
    game_state.current_phase = Phase.DELIBERATION

    for sub_round in [1, 2]:
        game_state.current_deliberation_round = sub_round

        # Get alive agents and shuffle them
        alive_agents = game_state.alive_agent_ids
        turn_order = random.sample(alive_agents, len(alive_agents))

        for agent_id in turn_order:
            context = ContextBuilder.build(game_state, agent_id)
            agent = agents[agent_id]

            output = await _deliberate_with_retry(
                agent=agent,
                context=context,
                agent_id=agent_id,
                episode_id=game_state.episode_id,
            )

            # Build PublicMessage for deliberation
            agent_config = next(
                a for a in game_state.config.agents if a.agent_id == agent_id
            )
            message = PublicMessage(
                agent_id=agent_id,
                display_name=agent_config.display_name,
                phase=Phase.DELIBERATION,
                round_number=game_state.current_round,
                deliberation_round=sub_round,
                content=output.public_statement,
                timestamp=datetime.now(UTC).isoformat(),
            )

            # Append to GameState immediately for next agents to see
            game_state.all_messages.append(message)

            # Emit Redis Event
            await emitter.emit(
                EVT_AGENT_DELIBERATED,
                {
                    "agent_id": agent_id,
                    "display_name": agent_config.display_name,
                    "public_statement": output.public_statement,
                    "phase": Phase.DELIBERATION,
                    "round_number": game_state.current_round,
                    "deliberation_round": sub_round,
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
