import asyncio
import random
from dataclasses import dataclass
from datetime import UTC, datetime

from src.engine.context_builder import ContextBuilder
from src.engine.event_emitter import (
    EVT_LAST_WORDS,
    EVT_ROLE_REVEAL,
    EVT_SURVIVOR_REACTED,
    EventEmitter,
)
from src.engine.exceptions import NodeError, RateLimitError
from src.models import (
    GameState,
    Phase,
    PublicMessage,
    Role,
    SystemAnnouncement,
)


@dataclass
class _ReactionResult:
    agent_id: str
    statement: str
    used_fallback: bool


async def reaction_node(
    state: GameState,
    agents: dict,
    emitter: EventEmitter,
) -> GameState:
    """
    Runs the reaction sequence after an elimination.

    1. Eliminated agent gives last words (sequential).
    2. System reveals the eliminated agent's role (sequential).
    3. Surviving agents react concurrently (shuffled output).

    Args:
        state:   Current GameState. Must have current_phase == Phase.REACTION.
        agents:  Mapping of agent_id → agent instance.
        emitter: EventEmitter connected to this episode's Redis channel.

    Returns:
        Mutated GameState with added messages and announcements.

    Raises:
        ValueError: if state.current_phase != Phase.REACTION.
        NodeError:  if state.elimination_result is None.
    """
    if state.current_phase != Phase.REACTION:
        raise ValueError(
            f"reaction_node requires Phase.REACTION, got {state.current_phase}"
        )

    if not state.elimination_result:
        raise NodeError(
            "reaction_node requires elimination_result to be populated.",
            node_name="reaction_node",
            episode_id=state.episode_id,
        )

    eliminated_id = state.elimination_result.eliminated_agent_id
    eliminated_agent = agents[eliminated_id]

    # --- Sequence 1: Last Words ---
    last_words_res = await _react_with_fallback(
        state,
        eliminated_agent,
        eliminated_id,
        fallback_text="*remains silent as they are dragged away*",
        is_eliminated_agent=True,
    )

    eliminated_agent_config = next(
        a for a in state.config.agents if a.agent_id == eliminated_id
    )
    last_words_msg = PublicMessage(
        agent_id=eliminated_id,
        display_name=eliminated_agent_config.display_name,
        phase=Phase.REACTION,
        round_number=state.current_round,
        deliberation_round=None,
        content=last_words_res.statement,
        timestamp=datetime.now(UTC).isoformat(),
    )
    state.all_messages.append(last_words_msg)

    await emitter.emit(
        EVT_LAST_WORDS,
        {
            "agent_id": eliminated_id,
            "statement": last_words_res.statement,
            "round_number": state.current_round,
        },
    )

    # --- Sequence 2: Role Reveal ---
    eliminated_role = state.role_assignments[eliminated_id].role

    reveal_content = (
        f"[SYSTEM] The eliminated agent ({eliminated_id}) was {eliminated_role.value}."
    )
    reveal_announcement = SystemAnnouncement(
        phase=Phase.REACTION,
        round_number=state.current_round,
        content=reveal_content,
        timestamp=datetime.now(UTC).isoformat(),
    )
    state.all_announcements.append(reveal_announcement)

    await emitter.emit(
        EVT_ROLE_REVEAL,
        {
            "agent_id": eliminated_id,
            "role": eliminated_role.value,
            "round_number": state.current_round,
        },
    )

    # --- Sequence 3: Survivor Reactions ---
    alive_survivor_ids = [aid for aid, alive in state.agent_alive.items() if alive]

    # Pre-calculate outcome context
    imposter_id = state.imposter_id
    game_outcome = "villagers_win" if eliminated_id == imposter_id else "imposter_wins"
    outcome_statement = (
        "The Villagers have won the game!"
        if game_outcome == "villagers_win"
        else "The Imposter has won the game!"
    )

    agent_names = {a.agent_id: a.display_name for a in state.config.agents}
    eliminated_name = agent_names.get(eliminated_id, "unknown")

    # Gather survivor reactions concurrently
    async def get_survivor_reaction(aid):
        vote = next((vr for vr in state.vote_records if vr.voter_agent_id == aid), None)
        vote_target_name = (
            agent_names.get(vote.target_agent_id, "unknown") if vote else "unknown"
        )

        voted_correctly = vote is not None and vote.target_agent_id == eliminated_id
        vote_correct_status = (
            "YES — you voted for the right person."
            if voted_correctly
            else "NO — you voted for the wrong person."
        )

        agent_role = state.role_assignments[aid].role
        is_imposter = agent_role == Role.IMPOSTER
        won_game = (game_outcome == "villagers_win" and not is_imposter) or (
            game_outcome == "imposter_wins" and is_imposter
        )
        you_won_status = "YOU WON this game." if won_game else "YOU LOST this game."

        return await _react_with_fallback(
            state,
            agents[aid],
            aid,
            fallback_text="*looks shocked and stays silent*",
            is_eliminated_agent=False,
            eliminated_agent_name=eliminated_name,
            eliminated_role=eliminated_role,
            outcome_statement=outcome_statement,
            last_words=last_words_res.statement,
            agent_vote_target=vote_target_name,
            game_outcome=game_outcome,
            vote_correct_status=vote_correct_status,
            you_won_status=you_won_status,
        )

    survivor_results: list[_ReactionResult] = await asyncio.gather(
        *[get_survivor_reaction(aid) for aid in alive_survivor_ids]
    )

    # Shuffle the results to avoid predictable reaction order in chat
    random.shuffle(survivor_results)

    for res in survivor_results:
        surv_agent_config = next(
            a for a in state.config.agents if a.agent_id == res.agent_id
        )
        msg = PublicMessage(
            agent_id=res.agent_id,
            display_name=surv_agent_config.display_name,
            phase=Phase.REACTION,
            round_number=state.current_round,
            deliberation_round=None,
            content=res.statement,
            timestamp=datetime.now(UTC).isoformat(),
        )
        state.all_messages.append(msg)

        await emitter.emit(
            EVT_SURVIVOR_REACTED,
            {
                "agent_id": res.agent_id,
                "statement": res.statement,
                "round_number": state.current_round,
            },
        )

    return state


async def _react_with_fallback(
    state: GameState, agent, agent_id: str, fallback_text: str, **kwargs
) -> _ReactionResult:
    """
    Calls agent.react(context, **kwargs).
    On invalid/failure: re-prompt once.
    On 2nd invalid: uses fallback_text.
    """
    import inspect

    context = ContextBuilder.build(state, agent_id)

    # Inspect the signature of agent.react to avoid TypeError on mock agents in tests
    sig = inspect.signature(agent.react)
    has_var_keyword = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
    )

    passed_kwargs = {}
    if has_var_keyword:
        passed_kwargs = kwargs
    else:
        for k, v in kwargs.items():
            if k in sig.parameters:
                passed_kwargs[k] = v

    for _attempt in range(2):
        try:
            output = await agent.react(context, **passed_kwargs)
            if (
                output
                and hasattr(output, "public_statement")
                and output.public_statement
            ):
                return _ReactionResult(
                    agent_id=agent_id,
                    statement=output.public_statement,
                    used_fallback=False,
                )
        except RateLimitError:
            raise
        except Exception:
            pass  # Fall through to retry/fallback

    # Random fallback
    return _ReactionResult(
        agent_id=agent_id,
        statement=fallback_text,
        used_fallback=True,
    )
