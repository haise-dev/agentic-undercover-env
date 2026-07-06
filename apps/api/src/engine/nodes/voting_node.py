import asyncio
import random
from dataclasses import dataclass

from src.engine.context_builder import ContextBuilder
from src.engine.event_emitter import (
    EVT_ELIMINATION_RESULT,
    EVT_VOTE_CAST,
    EventEmitter,
)
from src.engine.exceptions import NodeError, RateLimitError
from src.models import (
    EliminationResult,
    GameState,
    Phase,
    VoteRecord,
    VotingOutput,
)


@dataclass
class _VoteResult:
    voter_agent_id: str
    target_agent_id: str
    inner_thought: str
    used_fallback: bool


async def voting_node(
    state: GameState,
    agents: dict,
    emitter: EventEmitter,
) -> GameState:
    """
    Runs the concurrent voting phase.

    All alive agents vote simultaneously. Invalid votes are re-prompted once;
    second failure falls back to a random valid target. The agent with the
    most votes is eliminated; ties are broken randomly.

    Args:
        state:   Current GameState. Must have current_phase == Phase.VOTING.
        agents:  Mapping of agent_id → agent instance.
        emitter: EventEmitter connected to this episode's Redis channel.

    Returns:
        Mutated GameState with:
        - vote_records appended
        - elimination_result set
        - agent_alive[eliminated_id] = False

    Raises:
        ValueError: if state.current_phase != Phase.VOTING.
        NodeError:  if no valid voting targets exist (degenerate game state).
    """
    if state.current_phase != Phase.VOTING:
        raise ValueError(
            f"voting_node requires Phase.VOTING, got {state.current_phase}"
        )

    alive_ids = [
        aid for aid in state.current_turn_order if state.agent_alive.get(aid, False)
    ]

    # Step 1: concurrent voting
    results: list[_VoteResult] = await asyncio.gather(
        *[
            _vote_with_fallback(state, agents[agent_id], agent_id)
            for agent_id in alive_ids
        ]
    )

    # Step 2: build VoteRecords
    vote_records = [
        VoteRecord(
            voter_agent_id=r.voter_agent_id,
            target_agent_id=r.target_agent_id,
            inner_thought=r.inner_thought,
        )
        for r in results
    ]

    # Step 3: tally votes
    tally: dict[str, int] = {}
    for r in results:
        tally[r.target_agent_id] = tally.get(r.target_agent_id, 0) + 1

    # Step 4: determine elimination
    max_votes = max(tally.values())
    candidates = [t for t, v in tally.items() if v == max_votes]
    was_tiebreak = len(candidates) > 1
    eliminated_id = random.choice(candidates) if was_tiebreak else candidates[0]
    tiebreak_candidates = candidates if was_tiebreak else None

    elimination_result = EliminationResult(
        eliminated_agent_id=eliminated_id,
        vote_tally=tally,
        was_tiebreak=was_tiebreak,
        tiebreak_candidates=tiebreak_candidates,
    )

    # Step 5: mutate GameState
    state.vote_records.extend(vote_records)
    state.elimination_result = elimination_result
    state.agent_alive[eliminated_id] = False

    # Step 6: emit events
    for r in results:
        await emitter.emit(
            EVT_VOTE_CAST,
            {
                "voter_agent_id": r.voter_agent_id,
                "target_agent_id": r.target_agent_id,
                "round_number": state.current_round,
            },
        )

    await emitter.emit(
        EVT_ELIMINATION_RESULT,
        {
            "eliminated_agent_id": eliminated_id,
            "vote_tally": tally,
            "was_tiebreak": was_tiebreak,
            "tiebreak_candidates": tiebreak_candidates,
            "round_number": state.current_round,
        },
    )

    return state


async def _vote_with_fallback(state: GameState, agent, agent_id: str) -> _VoteResult:
    """
    Calls agent.vote(context).
    Validates: alive target, not self-vote.
    On invalid: re-prompt once.
    On 2nd invalid: random valid target.
    Returns _VoteResult.
    """
    valid_targets = [
        aid for aid in state.agent_alive if state.agent_alive[aid] and aid != agent_id
    ]
    if not valid_targets:
        raise NodeError(
            f"No valid voting targets for agent '{agent_id}'",
            node_name="voting_node",
            episode_id=state.episode_id,
        )

    context = ContextBuilder.build(state, agent_id)

    for _attempt in range(2):
        try:
            output = await agent.vote(context)
            if _is_valid_vote(output, agent_id, state):
                return _VoteResult(
                    voter_agent_id=agent_id,
                    target_agent_id=output.vote_target,
                    inner_thought=output.inner_thought,
                    used_fallback=False,
                )
        except RateLimitError:
            raise
        except Exception:
            pass  # fall through to retry/fallback

    # Random fallback
    fallback_target = random.choice(valid_targets)
    return _VoteResult(
        voter_agent_id=agent_id,
        target_agent_id=fallback_target,
        inner_thought="",
        used_fallback=True,
    )


def _is_valid_vote(output: object, voter_agent_id: str, state: GameState) -> bool:
    """Returns True if vote_target is alive and not a self-vote."""
    if not isinstance(output, VotingOutput):
        return False
    target = output.vote_target
    return (
        target != voter_agent_id
        and target in state.agent_alive
        and state.agent_alive[target]
    )
