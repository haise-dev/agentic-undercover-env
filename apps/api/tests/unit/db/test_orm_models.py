import uuid
from datetime import UTC, datetime

from src.db.models import ActionLogORM, Base, EpisodeORM


def test_orm_models_import_cleanly():
    assert EpisodeORM is not None
    assert ActionLogORM is not None
    assert Base is not None


def test_base_metadata_has_both_tables():
    tables = list(Base.metadata.tables.keys())
    assert "episodes" in tables
    assert "action_logs" in tables
    assert len(tables) == 2


def test_episode_orm_has_required_columns():
    assert EpisodeORM.__tablename__ == "episodes"

    episode_id = uuid.uuid4()
    now = datetime.now(UTC)

    episode = EpisodeORM(
        id=episode_id,
        config={"topic": "Fruit"},
        role_assignments=[{"agent_id": "agent_0"}],
        started_at=now,
        ended_at=now,
        result="villagers_win",
        elimination_result={"eliminated_agent_id": "agent_0"},
        export_json={"episode_id": str(episode_id)},
    )

    assert episode.id == episode_id
    assert episode.config == {"topic": "Fruit"}
    assert episode.role_assignments == [{"agent_id": "agent_0"}]
    assert episode.started_at == now
    assert episode.ended_at == now
    assert episode.result == "villagers_win"
    assert episode.elimination_result == {"eliminated_agent_id": "agent_0"}
    assert episode.export_json == {"episode_id": str(episode_id)}


def test_episode_orm_relationship_exists():
    # Verify the relationship is defined and has correct
    # cascade/back_populates properties
    rel = EpisodeORM.action_logs.property
    assert rel.target.name == "action_logs"
    assert rel.back_populates == "episode"
    assert rel.cascade.delete_orphan is True


def test_action_log_orm_has_required_columns():
    assert ActionLogORM.__tablename__ == "action_logs"

    log_id = uuid.uuid4()
    episode_id = uuid.uuid4()
    now = datetime.now(UTC)

    log = ActionLogORM(
        id=log_id,
        episode_id=episode_id,
        agent_id="agent_1",
        phase="speaking",
        round_number=1,
        deliberation_round=None,
        prompt_context={"test": True},
        raw_llm_response="hello",
        structured_output={"statement": "hello"},
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        latency_ms=250,
        timestamp=now,
    )

    assert log.id == log_id
    assert log.episode_id == episode_id
    assert log.agent_id == "agent_1"
    assert log.phase == "speaking"
    assert log.round_number == 1
    assert log.deliberation_round is None
    assert log.prompt_context == {"test": True}
    assert log.raw_llm_response == "hello"
    assert log.structured_output == {"statement": "hello"}
    assert log.prompt_tokens == 100
    assert log.completion_tokens == 50
    assert log.total_tokens == 150
    assert log.latency_ms == 250
    assert log.timestamp == now


def test_action_log_foreign_key_cascade():
    # Verify ForeignKey on episode_id
    fk_list = list(ActionLogORM.episode_id.property.columns[0].foreign_keys)
    assert len(fk_list) == 1
    fk = fk_list[0]
    assert fk.column.table.name == "episodes"
    assert fk.ondelete == "CASCADE"
