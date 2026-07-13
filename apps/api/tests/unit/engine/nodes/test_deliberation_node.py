import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.engine.event_emitter import EVT_AGENT_DELIBERATED, EventEmitter
from src.engine.exceptions import AgentOutputError
from src.engine.nodes.deliberation_node import (
    _is_valid_deliberation_output,
    deliberation_node,
)
from src.engine.graph.state import to_graph_state, to_game_state
from src.models import Phase, DeliberationOutput, DeliberationIntent
from tests.unit.engine.conftest import MockAgent


@pytest.fixture
def mock_emitter():
    emitter = MagicMock(spec=EventEmitter)
    emitter.emit = AsyncMock()
    return emitter


def ok_out(thought: str, statement: str) -> DeliberationOutput:
    return DeliberationOutput(
        inner_thought=thought,
        public_statement=statement,
        intent=DeliberationIntent.GENERAL_OPINION,
    )


@pytest.mark.asyncio
async def test_deliberation_node_success(game_state, mock_emitter):
    # Setup mock agents. 4 agents, each will speak twice (2 sub-rounds).
    # Thus, each needs 2 outputs.
    agents = {
        "agent_0": MockAgent(deliberate_outputs=[ok_out("t0_1", "s0_1"), ok_out("t0_2", "s0_2")]),
        "agent_1": MockAgent(deliberate_outputs=[ok_out("t1_1", "s1_1"), ok_out("t1_2", "s1_2")]),
        "agent_2": MockAgent(deliberate_outputs=[ok_out("t2_1", "s2_1"), ok_out("t2_2", "s2_2")]),
        "agent_3": MockAgent(deliberate_outputs=[ok_out("t3_1", "s3_1"), ok_out("t3_2", "s3_2")]),
    }

    graph_state = to_graph_state(game_state)

    # We want to patch random.sample to return fixed orders to verify logic easily.
    # sub-round 1: ["agent_3", "agent_2", "agent_1", "agent_0"]
    # sub-round 2: ["agent_1", "agent_0", "agent_3", "agent_2"]
    with patch("random.sample") as mock_sample:
        mock_sample.side_effect = [
            ["agent_3", "agent_2", "agent_1", "agent_0"],
            ["agent_1", "agent_0", "agent_3", "agent_2"],
        ]
        
        result_state = await deliberation_node(graph_state, agents, mock_emitter)

    # Verify return reference
    assert result_state is graph_state
    
    inner_game_state = to_game_state(result_state)
    assert inner_game_state.current_phase == Phase.DELIBERATION
    assert inner_game_state.current_deliberation_round == 2

    # Exactly 8 messages should have been added
    assert len(inner_game_state.all_messages) == 8
    
    # Verify sub-round 1 messages order
    sub_round_1_msgs = inner_game_state.all_messages[:4]
    assert [m.agent_id for m in sub_round_1_msgs] == ["agent_3", "agent_2", "agent_1", "agent_0"]
    for m in sub_round_1_msgs:
        assert m.phase == Phase.DELIBERATION
        assert m.deliberation_round == 1
        assert m.content == f"s{m.agent_id[-1]}_1"

    # Verify sub-round 2 messages order
    sub_round_2_msgs = inner_game_state.all_messages[4:]
    assert [m.agent_id for m in sub_round_2_msgs] == ["agent_1", "agent_0", "agent_3", "agent_2"]
    for m in sub_round_2_msgs:
        assert m.phase == Phase.DELIBERATION
        assert m.deliberation_round == 2
        assert m.content == f"s{m.agent_id[-1]}_2"

    # Verify event emitter calls (8 total EVT_AGENT_DELIBERATED events)
    assert mock_emitter.emit.call_count == 8
    calls = mock_emitter.emit.call_args_list
    
    # Check the first emit call
    args, kwargs = calls[0]
    assert args[0] == EVT_AGENT_DELIBERATED
    assert args[1]["agent_id"] == "agent_3"
    assert args[1]["deliberation_round"] == 1
    assert args[1]["public_statement"] == "s3_1"


@pytest.mark.asyncio
async def test_deliberation_node_retry_failure(game_state, mock_emitter):
    # Agent 0 fails all attempts in sub-round 1
    agents = {
        "agent_0": MockAgent(deliberate_outputs=[ValueError("Connection Timeout"), ValueError("Connection Timeout")]),
        "agent_1": MockAgent(deliberate_outputs=[ok_out("t1", "s1"), ok_out("t1_2", "s1_2")]),
        "agent_2": MockAgent(deliberate_outputs=[ok_out("t2", "s2"), ok_out("t2_2", "s2_2")]),
        "agent_3": MockAgent(deliberate_outputs=[ok_out("t3", "s3"), ok_out("t3_2", "s3_2")]),
    }

    graph_state = to_graph_state(game_state)

    with patch("random.sample") as mock_sample:
        # Agent 0 speaks first
        mock_sample.return_value = ["agent_0", "agent_1", "agent_2", "agent_3"]
        
        with pytest.raises(AgentOutputError) as exc_info:
            await deliberation_node(graph_state, agents, mock_emitter)

    assert exc_info.value.agent_id == "agent_0"
    assert exc_info.value.phase == "deliberation"
    assert "Connection Timeout" in str(exc_info.value)
    
    # Ensure no further agents are called
    assert len(agents["agent_1"].deliberate_calls) == 0


def test_is_valid_deliberation_output():
    valid = ok_out("thought", "hello")
    assert _is_valid_deliberation_output(valid) is True

    # Empty thoughts or statements
    assert _is_valid_deliberation_output(ok_out("", "hello")) is False
    assert _is_valid_deliberation_output(ok_out("thought", "")) is False
    assert _is_valid_deliberation_output(ok_out(" ", " ")) is False

    # Invalid type
    assert _is_valid_deliberation_output(None) is False
    assert _is_valid_deliberation_output("string") is False
