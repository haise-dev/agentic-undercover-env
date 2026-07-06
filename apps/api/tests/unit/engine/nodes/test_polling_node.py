import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.engine.event_emitter import EVT_POLL_RESULT, EventEmitter
from src.engine.exceptions import AgentOutputError
from src.engine.nodes.polling_node import (
    _is_valid_polling_output,
    polling_node,
)
from src.engine.graph.state import to_graph_state, to_game_state
from src.models import Phase, PollingOutput, PollVote
from tests.unit.engine.conftest import MockAgent


@pytest.fixture
def mock_emitter():
    emitter = MagicMock(spec=EventEmitter)
    emitter.emit = AsyncMock()
    return emitter


def ok_out(thought: str, vote: PollVote) -> PollingOutput:
    return PollingOutput(inner_thought=thought, poll_vote=vote)


@pytest.mark.asyncio
async def test_polling_node_concurrent_success_vote_now(game_state, mock_emitter):
    # Setup agents. 2 agents vote VOTE_NOW, 2 vote SKIP.
    # Total VOTE_NOW count = 2 -> proceed_to_vote = True.
    agents = {
        "agent_0": MockAgent(poll_outputs=[ok_out("t0", PollVote.VOTE_NOW)]),
        "agent_1": MockAgent(poll_outputs=[ok_out("t1", PollVote.SKIP)]),
        "agent_2": MockAgent(poll_outputs=[ok_out("t2", PollVote.VOTE_NOW)]),
        "agent_3": MockAgent(poll_outputs=[ok_out("t3", PollVote.SKIP)]),
    }

    graph_state = to_graph_state(game_state)
    result_state = await polling_node(graph_state, agents, mock_emitter)

    # Verify return reference
    assert result_state is graph_state
    
    # Assert proceed_to_vote is set to True
    assert result_state["proceed_to_vote"] is True
    
    inner_game_state = to_game_state(result_state)
    assert inner_game_state.current_phase == Phase.POLLING
    
    # Verify poll records are saved in game state
    poll_records = inner_game_state.poll_history[inner_game_state.current_round]
    assert len(poll_records) == 4
    
    # Map back to dict for easy assert
    records_dict = {r.agent_id: r for r in poll_records}
    assert records_dict["agent_0"].poll_vote == PollVote.VOTE_NOW
    assert records_dict["agent_1"].poll_vote == PollVote.SKIP
    assert records_dict["agent_2"].poll_vote == PollVote.VOTE_NOW
    assert records_dict["agent_3"].poll_vote == PollVote.SKIP

    # Verify event emitter
    mock_emitter.emit.assert_called_once_with(
        EVT_POLL_RESULT,
        {
            "vote_now_count": 2,
            "skip_count": 2,
            "forced": False,
        }
    )


@pytest.mark.asyncio
async def test_polling_node_concurrent_success_skip(game_state, mock_emitter):
    # Setup agents. 1 agent votes VOTE_NOW, 3 vote SKIP.
    # Total VOTE_NOW count = 1 -> proceed_to_vote = False.
    agents = {
        "agent_0": MockAgent(poll_outputs=[ok_out("t0", PollVote.SKIP)]),
        "agent_1": MockAgent(poll_outputs=[ok_out("t1", PollVote.SKIP)]),
        "agent_2": MockAgent(poll_outputs=[ok_out("t2", PollVote.VOTE_NOW)]),
        "agent_3": MockAgent(poll_outputs=[ok_out("t3", PollVote.SKIP)]),
    }

    graph_state = to_graph_state(game_state)
    result_state = await polling_node(graph_state, agents, mock_emitter)

    assert result_state["proceed_to_vote"] is False
    
    mock_emitter.emit.assert_called_once_with(
        EVT_POLL_RESULT,
        {
            "vote_now_count": 1,
            "skip_count": 3,
            "forced": False,
        }
    )


@pytest.mark.asyncio
async def test_polling_node_forced_vote_on_max_rounds(game_state, mock_emitter):
    # Setup state to max rounds (e.g. current_round = config.max_rounds)
    game_state.current_round = game_state.config.max_rounds

    # We do not define any poll_outputs because agents must NOT be called.
    agents = {
        "agent_0": MockAgent(),
        "agent_1": MockAgent(),
        "agent_2": MockAgent(),
        "agent_3": MockAgent(),
    }

    graph_state = to_graph_state(game_state)
    result_state = await polling_node(graph_state, agents, mock_emitter)

    # Forced is True, proceed_to_vote is True
    assert result_state["proceed_to_vote"] is True
    
    # Assert no agents were called
    for agent in agents.values():
        assert len(agent.poll_calls) == 0

    mock_emitter.emit.assert_called_once_with(
        EVT_POLL_RESULT,
        {
            "vote_now_count": 0,
            "skip_count": 0,
            "forced": True,
        }
    )


@pytest.mark.asyncio
async def test_polling_node_retry_failure(game_state, mock_emitter):
    # Agent 0 fails all attempts
    agents = {
        "agent_0": MockAgent(poll_outputs=[ValueError("Connection Timeout"), ValueError("Connection Timeout")]),
        "agent_1": MockAgent(poll_outputs=[ok_out("t1", PollVote.SKIP)]),
        "agent_2": MockAgent(poll_outputs=[ok_out("t2", PollVote.SKIP)]),
        "agent_3": MockAgent(poll_outputs=[ok_out("t3", PollVote.SKIP)]),
    }

    graph_state = to_graph_state(game_state)

    with pytest.raises(AgentOutputError) as exc_info:
        await polling_node(graph_state, agents, mock_emitter)

    assert exc_info.value.agent_id == "agent_0"
    assert exc_info.value.phase == "polling"
    assert "Connection Timeout" in str(exc_info.value)


def test_is_valid_polling_output():
    valid = ok_out("thought", PollVote.VOTE_NOW)
    assert _is_valid_polling_output(valid) is True

    # Empty thought
    assert _is_valid_polling_output(ok_out("", PollVote.VOTE_NOW)) is False
    assert _is_valid_polling_output(ok_out(" ", PollVote.VOTE_NOW)) is False

    # Invalid type
    assert _is_valid_polling_output(None) is False
    assert _is_valid_polling_output("string") is False
