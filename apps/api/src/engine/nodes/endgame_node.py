from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repository import EpisodeRepository
from src.engine.event_emitter import EVT_GAME_OVER, EventEmitter
from src.models import ActionLog, EpisodeExport, GameState
from src.models.enums import GameResult, Phase, Role


async def endgame_node(
    state: GameState,
    action_logs: list[ActionLog],
    db_session: AsyncSession,
    emitter: EventEmitter,
) -> EpisodeExport:
    """
    Finalizes the game status, builds the EpisodeExport, records log data,
    and emits the GAME_OVER event.

    Args:
        state:       Current GameState. Must have current_phase == Phase.ENDGAME.
        action_logs: List of all ActionLogs collected during the episode.
        db_session:  AsyncSession for database persistence.
        emitter:     EventEmitter for Redis events.

    Returns:
        The fully assembled EpisodeExport model.

    Raises:
        ValueError: if state.current_phase != Phase.ENDGAME.
    """
    if state.current_phase != Phase.ENDGAME:
        raise ValueError(
            f"endgame_node requires Phase.ENDGAME, got {state.current_phase}"
        )

    if not state.elimination_result:
        raise ValueError("endgame_node requires elimination_result to be populated")

    # --- 1. Determine Result ---
    imposter_id = state.imposter_id
    eliminated_id = state.elimination_result.eliminated_agent_id

    if eliminated_id == imposter_id:
        state.result = GameResult.VILLAGERS_WIN
        state.winning_agent_ids = [
            aid
            for aid, ra in state.role_assignments.items()
            if ra.role == Role.VILLAGER
        ]
    else:
        state.result = GameResult.IMPOSTER_WINS
        state.winning_agent_ids = [imposter_id]

    state.ended_at = datetime.now(UTC).isoformat()

    # --- 2. Assemble Stats ---
    started_dt = datetime.fromisoformat(state.started_at)
    ended_dt = datetime.fromisoformat(state.ended_at)
    duration_seconds = (ended_dt - started_dt).total_seconds()

    total_tokens_used = sum((log.total_tokens or 0) for log in action_logs)
    tokens_per_agent: dict[str, int | None] = {}
    for log in action_logs:
        if log.agent_id not in tokens_per_agent:
            tokens_per_agent[log.agent_id] = 0
        if log.total_tokens:
            tokens_per_agent[log.agent_id] += log.total_tokens  # type: ignore

    # Convert poll_history integer keys to strings for JSON compatibility
    string_poll_history = {str(k): v for k, v in state.poll_history.items()}

    export = EpisodeExport(
        episode_id=state.episode_id,
        started_at=state.started_at,
        ended_at=state.ended_at,
        duration_seconds=duration_seconds,
        config=state.config,
        role_assignments=list(state.role_assignments.values()),
        result=state.result,
        winning_agent_ids=state.winning_agent_ids,
        elimination_result=state.elimination_result,
        all_messages=state.all_messages,
        all_announcements=state.all_announcements,
        poll_history=string_poll_history,
        vote_records=state.vote_records,
        action_logs=action_logs,
        total_rounds_played=state.current_round,
        total_llm_calls=len(action_logs),
        total_tokens_used=total_tokens_used,
        tokens_per_agent=tokens_per_agent,
    )

    # --- 3. Database Persistence ---
    await EpisodeRepository.create(session=db_session, export=export)

    # --- 4. Event Emission ---
    # Find words to broadcast
    villager_word = ""
    imposter_word = ""
    for ra in state.role_assignments.values():
        if ra.role == Role.VILLAGER and not villager_word:
            villager_word = ra.secret_word
        elif ra.role == Role.IMPOSTER:
            imposter_word = ra.secret_word

    await emitter.emit(
        EVT_GAME_OVER,
        {
            "result": state.result.value,
            "winning_agent_ids": state.winning_agent_ids,
            "eliminated_agent_id": eliminated_id,
            "villager_word": villager_word,
            "imposter_word": imposter_word,
        },
    )

    return export
