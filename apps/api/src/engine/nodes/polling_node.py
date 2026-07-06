import asyncio

from src.engine.context_builder import ContextBuilder
from src.engine.event_emitter import (
    EVT_POLL_RESULT,
    EventEmitter,
)
from src.engine.exceptions import AgentOutputError, RateLimitError
from src.models import Phase, PollingOutput, PollRecord, PollVote

_MAX_POLL_ATTEMPTS = 2


async def polling_node(
    state: dict | object,
    agents: dict,
    emitter: EventEmitter,
) -> dict | object:
    """
    Runs the Polling Phase:
    - If max_rounds is reached, bypass LLM calls and force vote.
    - Otherwise, query all alive agents concurrently using asyncio.gather.
    - Tally results: if >= 2 agents vote to VOTE_NOW, proceed_to_vote = True,
      otherwise proceed_to_vote = False.
    - Record the polling history in GameState and emit Redis event.

    Args:
        state: LangGraph GraphState (dict) or GameState.
        agents: Dictionary of agent_id -> AIAgent.
        emitter: Redis EventEmitter.

    Returns:
        GraphState (dict) or GameState containing the mutated GameState and proceed_to_vote flag.

    Raises:
        AgentOutputError: If any agent fails to produce a valid response.
    """
    is_graph_state = isinstance(state, dict) and "game_state" in state
    game_state = state["game_state"] if is_graph_state else state
    game_state.current_phase = Phase.POLLING

    is_forced = game_state.current_round >= game_state.config.max_rounds

    if is_forced:
        if is_graph_state:
            state["proceed_to_vote"] = True
        vote_now_count = 0
        skip_count = 0
    else:
        alive_agents = game_state.alive_agent_ids

        # Concurrently build contexts and poll agents
        tasks = []
        for agent_id in alive_agents:
            context = ContextBuilder.build(game_state, agent_id)
            agent = agents[agent_id]
            tasks.append(
                _poll_with_retry(
                    agent=agent,
                    context=context,
                    agent_id=agent_id,
                    episode_id=game_state.episode_id,
                )
            )

        # Run concurrent LLM calls
        outputs = await asyncio.gather(*tasks)

        # Tally and create records
        vote_now_count = 0
        skip_count = 0
        records = []

        for agent_id, output in zip(alive_agents, outputs):
            if output.poll_vote == PollVote.VOTE_NOW:
                vote_now_count += 1
            else:
                skip_count += 1

            records.append(
                PollRecord(
                    agent_id=agent_id,
                    poll_vote=output.poll_vote,
                    inner_thought=output.inner_thought,
                    round_number=game_state.current_round,
                )
            )

        # Store records in history
        game_state.poll_history[game_state.current_round] = records
        if is_graph_state:
            state["proceed_to_vote"] = vote_now_count >= 2

    # Emit Redis event
    await emitter.emit(
        EVT_POLL_RESULT,
        {
            "vote_now_count": vote_now_count,
            "skip_count": skip_count,
            "forced": is_forced,
        },
    )

    return state


async def _poll_with_retry(
    agent,
    context,
    agent_id: str,
    episode_id: str,
) -> PollingOutput:
    """
    Invokes agent.poll() with retries.
    Raises AgentOutputError on exhaustion.
    """
    last_exc: Exception | None = None
    for attempt in range(_MAX_POLL_ATTEMPTS):
        try:
            output = await agent.poll(context)
            if _is_valid_polling_output(output):
                return output
            last_exc = ValueError(
                f"Agent '{agent_id}' produced invalid PollingOutput "
                f"on attempt {attempt + 1}: "
                f"inner_thought={repr(output.inner_thought)!r}, "
                f"poll_vote={repr(output.poll_vote)!r}"
            )
        except RateLimitError:
            raise
        except Exception as exc:
            last_exc = exc

    raise AgentOutputError(
        message=(
            f"Agent '{agent_id}' failed to produce valid PollingOutput "
            f"after {_MAX_POLL_ATTEMPTS} attempts. Last error: {last_exc}"
        ),
        agent_id=agent_id,
        phase="polling",
        episode_id=episode_id,
    )


def _is_valid_polling_output(output: object) -> bool:
    """Checks if the output matches the required PollingOutput format."""
    return (
        isinstance(output, PollingOutput)
        and bool(output.inner_thought.strip())
        and isinstance(output.poll_vote, PollVote)
    )
