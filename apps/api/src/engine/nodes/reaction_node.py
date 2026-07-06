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

    # Gather survivor reactions concurrently
    survivor_results: list[_ReactionResult] = await asyncio.gather(
        *[
            _react_with_fallback(
                state,
                agents[aid],
                aid,
                fallback_text="*looks shocked and stays silent*",
            )
            for aid in alive_survivor_ids
        ]
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
    state: GameState, agent, agent_id: str, fallback_text: str
) -> _ReactionResult:
    """
    Calls agent.react(context).
    On invalid/failure: re-prompt once.
    On 2nd invalid: uses fallback_text.
    """
    context = ContextBuilder.build(state, agent_id)

    for _attempt in range(2):
        try:
            output = await agent.react(context)
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
