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


def ok_out_intent(
    thought: str,
    statement: str,
    intent: DeliberationIntent,
    target_name: str | None = None,
) -> DeliberationOutput:
    return DeliberationOutput(
        inner_thought=thought,
        public_statement=statement,
        intent=intent,
        target_name=target_name,
    )


@pytest.mark.asyncio
async def test_deliberation_node_resets_on_first_entry(game_state, mock_emitter):
    game_state.current_phase = Phase.SPEAKING
    game_state.next_speaker_id = "agent_0"
    game_state.turns_count = {"agent_0": 5}  # Should be cleared
    game_state.speakers_this_round = {"agent_0"}  # Should be cleared
    game_state.deliberation_message_count = 5  # Should be cleared

    agents = {"agent_0": MockAgent(deliberate_outputs=[ok_out("t0", "s0")])}
    graph_state = to_graph_state(game_state)

    result_state = await deliberation_node(graph_state, agents, mock_emitter)
    inner_game_state = to_game_state(result_state)

    assert inner_game_state.current_phase == Phase.DELIBERATION
    assert inner_game_state.deliberation_message_count == 1
    assert inner_game_state.turns_count == {"agent_0": 1}
    assert inner_game_state.speakers_this_round == {"agent_0"}
    assert inner_game_state.next_speaker_id is None


@pytest.mark.asyncio
async def test_deliberation_node_no_reset_on_subsequent_call(game_state, mock_emitter):
    game_state.current_phase = Phase.DELIBERATION
    game_state.next_speaker_id = "agent_1"
    game_state.turns_count = {"agent_0": 1}
    game_state.speakers_this_round = {"agent_0"}
    game_state.deliberation_message_count = 1

    agents = {"agent_1": MockAgent(deliberate_outputs=[ok_out("t1", "s1")])}
    graph_state = to_graph_state(game_state)

    result_state = await deliberation_node(graph_state, agents, mock_emitter)
    inner_game_state = to_game_state(result_state)

    assert inner_game_state.deliberation_message_count == 2
    assert inner_game_state.turns_count == {"agent_0": 1, "agent_1": 1}
    assert inner_game_state.speakers_this_round == {"agent_0", "agent_1"}


@pytest.mark.asyncio
async def test_deliberation_node_appends_message(game_state, mock_emitter):
    game_state.current_phase = Phase.DELIBERATION
    game_state.next_speaker_id = "agent_0"

    agents = {"agent_0": MockAgent(deliberate_outputs=[ok_out("t0", "s0")])}
    graph_state = to_graph_state(game_state)

    await deliberation_node(graph_state, agents, mock_emitter)
    assert len(game_state.all_messages) == 1
    msg = game_state.all_messages[0]
    assert msg.agent_id == "agent_0"
    assert msg.phase == Phase.DELIBERATION
    assert msg.content == "s0"


@pytest.mark.asyncio
async def test_deliberation_node_emits_event_with_intent(game_state, mock_emitter):
    game_state.current_phase = Phase.DELIBERATION
    game_state.next_speaker_id = "agent_0"

    agents = {
        "agent_0": MockAgent(
            deliberate_outputs=[
                ok_out_intent("t0", "s0", DeliberationIntent.ACCUSE, "agent_1")
            ]
        )
    }
    graph_state = to_graph_state(game_state)

    await deliberation_node(graph_state, agents, mock_emitter)
    mock_emitter.emit.assert_called_once()
    args, kwargs = mock_emitter.emit.call_args
    assert args[0] == EVT_AGENT_DELIBERATED
    payload = args[1]
    assert payload["agent_id"] == "agent_0"
    assert payload["public_statement"] == "s0"
    assert payload["intent"] == DeliberationIntent.ACCUSE
    assert payload["target_name"] == "agent_1"


@pytest.mark.asyncio
async def test_deliberation_node_raises_if_no_next_speaker(game_state, mock_emitter):
    game_state.current_phase = Phase.DELIBERATION
    game_state.next_speaker_id = None

    graph_state = to_graph_state(game_state)
    with pytest.raises(ValueError, match="next_speaker_id=None"):
        await deliberation_node(graph_state, {}, mock_emitter)


@pytest.mark.asyncio
async def test_deliberation_node_accumulates_turns_count(game_state, mock_emitter):
    game_state.current_phase = Phase.DELIBERATION
    game_state.next_speaker_id = "agent_0"
    game_state.turns_count = {"agent_0": 1}

    agents = {"agent_0": MockAgent(deliberate_outputs=[ok_out("t0", "s0")])}
    graph_state = to_graph_state(game_state)

    await deliberation_node(graph_state, agents, mock_emitter)
    assert game_state.turns_count["agent_0"] == 2


@pytest.mark.asyncio
async def test_deliberation_node_retry_failure(game_state, mock_emitter):
    game_state.current_phase = Phase.DELIBERATION
    game_state.next_speaker_id = "agent_0"

    agents = {
        "agent_0": MockAgent(
            deliberate_outputs=[
                ValueError("Connection Timeout"),
                ValueError("Connection Timeout"),
            ]
        )
    }
    graph_state = to_graph_state(game_state)

    with pytest.raises(AgentOutputError) as exc_info:
        await deliberation_node(graph_state, agents, mock_emitter)

    assert exc_info.value.agent_id == "agent_0"
    assert exc_info.value.phase == "deliberation"
    assert "Connection Timeout" in str(exc_info.value)
    assert game_state.deliberation_message_count == 0



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
