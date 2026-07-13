import asyncio
import random
from dataclasses import dataclass

from src.engine.context_builder import ContextBuilder
from src.engine.event_emitter import (
    EVT_ELIMINATION_RESULT,
    EVT_VOTE_CAST,
    EVT_VOTING_STARTED,
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

    await emitter.emit(
        EVT_VOTING_STARTED,
        {
            "round_number": state.current_round,
        },
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
                "inner_thought": r.inner_thought,
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
            if isinstance(output, VotingOutput):
                resolved_id = _resolve_agent_id(output.vote_target, state)
                # Ensure it's not a self-vote and is a valid alive agent
                if resolved_id and resolved_id != agent_id:
                    return _VoteResult(
                        voter_agent_id=agent_id,
                        target_agent_id=resolved_id,
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


def _resolve_agent_id(target: str, state: GameState) -> str | None:
    """
    Resolves a target string (which could be an agent_id or a display_name)
    to a valid agent_id from the alive agents.
    Returns None if not resolvable or if target agent is dead.
    """
    if not target or not isinstance(target, str):
        return None

    # 1. Try resolving as a direct agent_id
    target_id = target.strip()
    if target_id in state.agent_alive and state.agent_alive[target_id]:
        return target_id

    # 2. Try resolving as a display_name (case-insensitive, stripped)
    target_clean = target_id.lower()
    for agent in state.config.agents:
        if agent.display_name.strip().lower() == target_clean:
            aid = agent.agent_id
            if state.agent_alive.get(aid, False):
                return aid

    return None
