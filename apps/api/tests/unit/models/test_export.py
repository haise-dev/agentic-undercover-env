import pytest
from pydantic import ValidationError

from src.models.enums import GameResult, Phase
from src.models.export import ActionLog, EpisodeExport
from src.models.votes import EliminationResult


def test_action_log_minimal():
    log = ActionLog(
        episode_id="uuid-123",
        agent_id="agent_1",
        phase=Phase.SPEAKING,
        round_number=1,
        prompt_context={},
        raw_llm_response="raw",
        structured_output={},
        timestamp="2026-07-02T10:00:00Z",
    )
    assert log.episode_id == "uuid-123"
    assert log.prompt_tokens is None


def test_action_log_with_token_usage():
    log = ActionLog(
        episode_id="uuid-123",
        agent_id="agent_1",
        phase=Phase.SPEAKING,
        round_number=1,
        prompt_context={},
        raw_llm_response="raw",
        structured_output={},
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        timestamp="2026-07-02T10:00:00Z",
        latency_ms=150,
    )
    assert log.total_tokens == 30
    assert log.latency_ms == 150


def test_action_log_frozen():
    log = ActionLog(
        episode_id="uuid-123",
        agent_id="agent_1",
        phase=Phase.SPEAKING,
        round_number=1,
        prompt_context={},
        raw_llm_response="raw",
        structured_output={},
        timestamp="2026-07-02T10:00:00Z",
    )
    with pytest.raises(ValidationError):
        log.episode_id = "new-uuid"


def test_action_log_serializable():
    log = ActionLog(
        episode_id="uuid-123",
        agent_id="agent_1",
        phase=Phase.SPEAKING,
        round_number=1,
        prompt_context={},
        raw_llm_response="raw",
        structured_output={},
        timestamp="2026-07-02T10:00:00Z",
    )
    dumped = log.model_dump()
    assert isinstance(dumped, dict)
    assert dumped["episode_id"] == "uuid-123"


def test_episode_export_complete(episode_config, role_assignments):
    er = EliminationResult(
        eliminated_agent_id="agent_0", vote_tally={"agent_0": 3}, was_tiebreak=False
    )
    export = EpisodeExport(
        episode_id="uuid-123",
        started_at="2026-07-02T10:00:00Z",
        ended_at="2026-07-02T10:02:00Z",
        duration_seconds=120.0,
        config=episode_config,
        role_assignments=list(role_assignments.values()),
        result=GameResult.VILLAGERS_WIN,
        winning_agent_ids=["agent_1", "agent_2", "agent_3"],
        elimination_result=er,
        all_messages=[],
        all_announcements=[],
        poll_history={},
        vote_records=[],
        action_logs=[],
        total_rounds_played=1,
        total_llm_calls=8,
        total_tokens_used=4000,
        tokens_per_agent={"agent_0": 1000, "agent_1": 1000},
    )
    assert export.episode_id == "uuid-123"
    assert export.duration_seconds == 120.0


def test_episode_export_frozen(episode_config, role_assignments):
    er = EliminationResult(
        eliminated_agent_id="agent_0", vote_tally={"agent_0": 3}, was_tiebreak=False
    )
    export = EpisodeExport(
        episode_id="uuid-123",
        started_at="2026-07-02T10:00:00Z",
        ended_at="2026-07-02T10:02:00Z",
        duration_seconds=120.0,
        config=episode_config,
        role_assignments=list(role_assignments.values()),
        result=GameResult.VILLAGERS_WIN,
        winning_agent_ids=["agent_1", "agent_2", "agent_3"],
        elimination_result=er,
        all_messages=[],
        all_announcements=[],
        poll_history={},
        vote_records=[],
        action_logs=[],
        total_rounds_played=1,
        total_llm_calls=8,
        total_tokens_used=4000,
        tokens_per_agent={"agent_0": 1000, "agent_1": 1000},
    )
    with pytest.raises(ValidationError):
        export.duration_seconds = 200.0


def test_episode_export_serializable(episode_config, role_assignments):
    er = EliminationResult(
        eliminated_agent_id="agent_0", vote_tally={"agent_0": 3}, was_tiebreak=False
    )
    export = EpisodeExport(
        episode_id="uuid-123",
        started_at="2026-07-02T10:00:00Z",
        ended_at="2026-07-02T10:02:00Z",
        duration_seconds=120.0,
        config=episode_config,
        role_assignments=list(role_assignments.values()),
        result=GameResult.VILLAGERS_WIN,
        winning_agent_ids=["agent_1", "agent_2", "agent_3"],
        elimination_result=er,
        all_messages=[],
        all_announcements=[],
        poll_history={},
        vote_records=[],
        action_logs=[],
        total_rounds_played=1,
        total_llm_calls=8,
        total_tokens_used=4000,
        tokens_per_agent={"agent_0": 1000, "agent_1": 1000},
    )
    dumped = export.model_dump()
    assert isinstance(dumped, dict)
    assert dumped["episode_id"] == "uuid-123"


def test_episode_export_poll_history_str_keys(episode_config, role_assignments):
    er = EliminationResult(
        eliminated_agent_id="agent_0", vote_tally={"agent_0": 3}, was_tiebreak=False
    )
    export = EpisodeExport(
        episode_id="uuid-123",
        started_at="2026-07-02T10:00:00Z",
        ended_at="2026-07-02T10:02:00Z",
        duration_seconds=120.0,
        config=episode_config,
        role_assignments=list(role_assignments.values()),
        result=GameResult.VILLAGERS_WIN,
        winning_agent_ids=["agent_1", "agent_2", "agent_3"],
        elimination_result=er,
        all_messages=[],
        all_announcements=[],
        poll_history={"1": []},
        vote_records=[],
        action_logs=[],
        total_rounds_played=1,
        total_llm_calls=8,
        total_tokens_used=4000,
        tokens_per_agent={"agent_0": 1000, "agent_1": 1000},
    )
    assert "1" in export.poll_history


# Flat import integration tests
def test_flat_import_enums():
    from src.models import Phase, Role

    assert Role.IMPOSTER == "imposter"
    assert Phase.INIT == "init"


def test_flat_import_gamestate():
    from src.models import GameState

    assert GameState is not None


def test_flat_import_all_outputs():
    from src.models import SpeakingOutput, VotingOutput

    assert SpeakingOutput is not None
    assert VotingOutput is not None


def test_all_exports_listed():
    import src.models

    assert len(src.models.__all__) == 26

