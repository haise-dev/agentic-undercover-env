from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.engine.event_emitter import EVT_GAME_OVER, EventEmitter
from src.engine.nodes.endgame_node import endgame_node
from src.models import ActionLog, EpisodeExport
from src.models.assignment import AgentRoleAssignment
from src.models.enums import GameResult, Phase, Role
from src.models.votes import EliminationResult


@pytest.fixture
def mock_emitter():
    emitter = MagicMock(spec=EventEmitter)
    emitter.emit = AsyncMock()
    return emitter


@pytest.fixture
def mock_db_session():
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def endgame_state(game_state):
    game_state.current_phase = Phase.ENDGAME
    game_state.started_at = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    # Mocking a game with 4 agents: agent_0 to agent_3
    # Let's say agent_1 is the Imposter
    game_state.role_assignments = {
        "agent_0": AgentRoleAssignment(
            agent_id="agent_0", role=Role.VILLAGER, secret_word="Apple", topic="Fruit"
        ),
        "agent_1": AgentRoleAssignment(
            agent_id="agent_1", role=Role.IMPOSTER, secret_word="Pear", topic="Fruit"
        ),
        "agent_2": AgentRoleAssignment(
            agent_id="agent_2", role=Role.VILLAGER, secret_word="Apple", topic="Fruit"
        ),
        "agent_3": AgentRoleAssignment(
            agent_id="agent_3", role=Role.VILLAGER, secret_word="Apple", topic="Fruit"
        ),
    }
    game_state.current_round = 3
    # Dummy poll history with int keys
    game_state.poll_history = {1: [], 2: [], 3: []}
    return game_state


@pytest.fixture
def action_logs():
    return [
        ActionLog(
            episode_id="some_ep",
            agent_id="agent_0",
            phase=Phase.SPEAKING,
            round_number=1,
            prompt_context={},
            raw_llm_response="",
            structured_output={},
            total_tokens=100,
            timestamp=datetime.now(UTC).isoformat(),
        ),
        ActionLog(
            episode_id="some_ep",
            agent_id="agent_1",
            phase=Phase.SPEAKING,
            round_number=1,
            prompt_context={},
            raw_llm_response="",
            structured_output={},
            total_tokens=150,
            timestamp=datetime.now(UTC).isoformat(),
        ),
    ]


@pytest.mark.asyncio
async def test_endgame_node_phase_guard(
    game_state, action_logs, mock_db_session, mock_emitter
):
    game_state.current_phase = Phase.REACTION
    with pytest.raises(ValueError, match="endgame_node requires Phase.ENDGAME"):
        await endgame_node(game_state, action_logs, mock_db_session, mock_emitter)


@pytest.mark.asyncio
@patch("src.engine.nodes.endgame_node.EpisodeRepository.create", new_callable=AsyncMock)
async def test_endgame_villagers_win(
    mock_repo_create, endgame_state, action_logs, mock_db_session, mock_emitter
):
    # Imposter is agent_1. They get eliminated.
    endgame_state.elimination_result = EliminationResult(
        eliminated_agent_id="agent_1",
        vote_tally={"agent_1": 3, "agent_0": 1},
        was_tiebreak=False,
        tiebreak_candidates=None,
    )

    export = await endgame_node(
        endgame_state, action_logs, mock_db_session, mock_emitter
    )

    # State mutations
    assert endgame_state.result == GameResult.VILLAGERS_WIN
    assert set(endgame_state.winning_agent_ids) == {"agent_0", "agent_2", "agent_3"}
    assert endgame_state.ended_at is not None

    # Export assertions
    assert isinstance(export, EpisodeExport)
    assert export.result == GameResult.VILLAGERS_WIN
    assert set(export.winning_agent_ids) == {"agent_0", "agent_2", "agent_3"}
    assert export.total_rounds_played == 3
    assert export.total_llm_calls == 2
    assert export.total_tokens_used == 250
    assert export.tokens_per_agent["agent_0"] == 100
    assert export.tokens_per_agent["agent_1"] == 150
    assert "agent_2" not in export.tokens_per_agent

    # Check poll history integer stringification
    assert "1" in export.poll_history
    assert "2" in export.poll_history

    # DB Persistence
    mock_repo_create.assert_awaited_once_with(session=mock_db_session, export=export)

    # Event Emission
    mock_emitter.emit.assert_awaited_once()
    call_args = mock_emitter.emit.await_args[0]
    assert call_args[0] == EVT_GAME_OVER
    payload = call_args[1]
    assert payload["result"] == GameResult.VILLAGERS_WIN.value
    assert set(payload["winning_agent_ids"]) == {"agent_0", "agent_2", "agent_3"}
    assert payload["eliminated_agent_id"] == "agent_1"
    assert payload["villager_word"] == "Apple"
    assert payload["imposter_word"] == "Pear"


@pytest.mark.asyncio
@patch("src.engine.nodes.endgame_node.EpisodeRepository.create", new_callable=AsyncMock)
async def test_endgame_imposter_wins(
    mock_repo_create, endgame_state, action_logs, mock_db_session, mock_emitter
):
    # Villager (agent_0) gets eliminated.
    endgame_state.elimination_result = EliminationResult(
        eliminated_agent_id="agent_0",
        vote_tally={"agent_0": 3, "agent_1": 1},
        was_tiebreak=False,
        tiebreak_candidates=None,
    )

    export = await endgame_node(
        endgame_state, action_logs, mock_db_session, mock_emitter
    )

    # State mutations
    assert endgame_state.result == GameResult.IMPOSTER_WINS
    assert endgame_state.winning_agent_ids == ["agent_1"]

    # Export assertions
    assert export.result == GameResult.IMPOSTER_WINS
    assert export.winning_agent_ids == ["agent_1"]

    # Event Emission
    call_args = mock_emitter.emit.await_args[0]
    payload = call_args[1]
    assert payload["result"] == GameResult.IMPOSTER_WINS.value
    assert payload["winning_agent_ids"] == ["agent_1"]
    assert payload["eliminated_agent_id"] == "agent_0"
