import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.models import Base, EpisodeORM
from src.db.repository import ActionLogRepository, EpisodeRepository
from src.models import (
    ActionLog,
    AgentRoleAssignment,
    EliminationResult,
    EpisodeConfig,
    EpisodeExport,
    GameResult,
    Phase,
    Role,
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    # Enable foreign key support in SQLite
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture
async def db_session():
    """Provides an AsyncSession connected to a local SQLite test DB.

    Creates all tables before the test, drops them and deletes the file after.
    """
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

    if os.path.exists("./test.db"):
        try:
            os.remove("./test.db")
        except Exception:
            pass


@pytest.fixture
def sample_export(episode_config) -> EpisodeExport:
    """Helper to construct a realistic EpisodeExport."""
    er = EliminationResult(
        eliminated_agent_id="agent_0",
        vote_tally={"agent_0": 3, "agent_1": 1},
        was_tiebreak=False,
    )
    role_assigns = [
        AgentRoleAssignment(
            agent_id="agent_0",
            role=Role.IMPOSTER,
            secret_word=None,
            topic="Fruit",
        ),
        AgentRoleAssignment(
            agent_id="agent_1",
            role=Role.VILLAGER,
            secret_word="Durian",
            topic="Fruit",
        ),
        AgentRoleAssignment(
            agent_id="agent_2",
            role=Role.VILLAGER,
            secret_word="Durian",
            topic="Fruit",
        ),
        AgentRoleAssignment(
            agent_id="agent_3",
            role=Role.VILLAGER,
            secret_word="Durian",
            topic="Fruit",
        ),
    ]
    log1 = ActionLog(
        episode_id=episode_config.episode_id,
        agent_id="agent_1",
        phase=Phase.SPEAKING,
        round_number=1,
        prompt_context={"test": True},
        raw_llm_response="raw text 1",
        structured_output={"public_statement": "statement 1"},
        timestamp="2026-07-02T10:00:00Z",
    )
    log2 = ActionLog(
        episode_id=episode_config.episode_id,
        agent_id="agent_2",
        phase=Phase.SPEAKING,
        round_number=1,
        prompt_context={"test": True},
        raw_llm_response="raw text 2",
        structured_output={"public_statement": "statement 2"},
        timestamp="2026-07-02T10:00:05Z",
    )

    return EpisodeExport(
        episode_id=episode_config.episode_id,
        started_at="2026-07-02T10:00:00Z",
        ended_at="2026-07-02T10:02:00Z",
        duration_seconds=120.0,
        config=episode_config,
        role_assignments=role_assigns,
        result=GameResult.VILLAGERS_WIN,
        winning_agent_ids=["agent_1", "agent_2", "agent_3"],
        elimination_result=er,
        all_messages=[],
        all_announcements=[],
        poll_history={},
        vote_records=[],
        action_logs=[log1, log2],
        total_rounds_played=1,
        total_llm_calls=2,
        total_tokens_used=1000,
        tokens_per_agent={"agent_1": 500, "agent_2": 500},
    )


@pytest.mark.asyncio
async def test_create_and_retrieve_episode(db_session, sample_export):
    # Save the episode
    episode_uuid = await EpisodeRepository.create(db_session, sample_export)
    assert episode_uuid == uuid.UUID(sample_export.episode_id)

    # Commit/flush is managed by test, retrieve back
    retrieved = await EpisodeRepository.get_by_id(db_session, sample_export.episode_id)

    assert retrieved is not None
    assert retrieved.episode_id == sample_export.episode_id
    assert retrieved.result == sample_export.result
    assert retrieved.config.topic == sample_export.config.topic
    assert len(retrieved.action_logs) == len(sample_export.action_logs)


@pytest.mark.asyncio
async def test_create_episode_and_retrieve_action_logs(db_session, sample_export):
    await EpisodeRepository.create(db_session, sample_export)

    # Retrieve logs independently
    logs = await ActionLogRepository.get_by_episode(
        db_session, sample_export.episode_id
    )

    assert len(logs) == 2
    assert logs[0].agent_id == "agent_1"
    assert logs[1].agent_id == "agent_2"
    # Verify timestamp order (ascending)
    assert logs[0].timestamp < logs[1].timestamp


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_missing(db_session):
    retrieved = await EpisodeRepository.get_by_id(db_session, str(uuid.uuid4()))
    assert retrieved is None

    # Test invalid UUID string
    retrieved = await EpisodeRepository.get_by_id(db_session, "invalid-uuid")
    assert retrieved is None


@pytest.mark.asyncio
async def test_list_recent_returns_correct_fields(db_session, sample_export):
    await EpisodeRepository.create(db_session, sample_export)

    # Create another episode with different ID
    another_export = sample_export.model_copy(deep=True)
    another_id = str(uuid.uuid4())
    # Modify ID in copy
    another_export = another_export.model_copy(update={"episode_id": another_id})

    await EpisodeRepository.create(db_session, another_export)

    recent = await EpisodeRepository.list_recent(db_session, limit=10)

    assert len(recent) == 2
    for ep in recent:
        assert "id" in ep
        assert "started_at" in ep
        assert "ended_at" in ep
        assert "result" in ep
        assert "total_rounds_played" in ep
        # Verify it doesn't contain heavy fields
        assert "config" not in ep
        assert "export_json" not in ep


@pytest.mark.asyncio
async def test_duplicate_episode_id_raises(db_session, sample_export):
    await EpisodeRepository.create(db_session, sample_export)

    # Attempt to create duplicate should raise IntegrityError
    with pytest.raises(IntegrityError):
        await EpisodeRepository.create(db_session, sample_export)


@pytest.mark.asyncio
async def test_delete_episode_cascades_to_action_logs(db_session, sample_export):
    episode_uuid = await EpisodeRepository.create(db_session, sample_export)

    # Verify action logs exist
    logs = await ActionLogRepository.get_by_episode(
        db_session, sample_export.episode_id
    )
    assert len(logs) == 2

    # Delete episode
    stmt = delete(EpisodeORM).where(EpisodeORM.id == episode_uuid)
    await db_session.execute(stmt)
    await db_session.flush()

    # Verify action logs are cascade-deleted
    logs_after = await ActionLogRepository.get_by_episode(
        db_session, sample_export.episode_id
    )
    assert len(logs_after) == 0


@pytest.mark.asyncio
async def test_episode_export_round_trip_preserves_pydantic_types(
    db_session, sample_export
):
    await EpisodeRepository.create(db_session, sample_export)

    retrieved = await EpisodeRepository.get_by_id(db_session, sample_export.episode_id)

    assert isinstance(retrieved, EpisodeExport)
    assert isinstance(retrieved.result, GameResult)
    assert isinstance(retrieved.config, EpisodeConfig)
    assert isinstance(retrieved.role_assignments[0], AgentRoleAssignment)
    assert isinstance(retrieved.action_logs[0], ActionLog)


@pytest.mark.asyncio
async def test_bulk_insert_empty_logs(db_session):
    res = await ActionLogRepository.bulk_insert(db_session, uuid.uuid4(), [])
    assert res == 0


@pytest.mark.asyncio
async def test_get_by_episode_invalid_uuid(db_session):
    res = await ActionLogRepository.get_by_episode(db_session, "invalid-uuid")
    assert res == []
