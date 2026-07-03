import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.engine.event_emitter import EVT_AGENT_SPOKE, EVT_ROUND_STARTED, EventEmitter
from src.engine.exceptions import AgentOutputError
from src.engine.nodes.speaking_node import (
    _is_valid_speaking_output,
    speaking_node,
)
from src.models import Phase, SpeakingOutput
from tests.unit.engine.conftest import MockAgent


# --- Mock EventEmitter fixture ---
@pytest.fixture
def mock_emitter():
    emitter = MagicMock(spec=EventEmitter)
    emitter.emit = AsyncMock()
    return emitter


# --- Helper to create game state in speaking phase ---
@pytest.fixture
def speaking_state(game_state):
    game_state.current_phase = Phase.SPEAKING
    return game_state


# --- Helper to make SpeakingOutput concisely ---
def ok_out(thought: str, statement: str) -> SpeakingOutput:
    return SpeakingOutput(inner_thought=thought, public_statement=statement)


@pytest.mark.asyncio
async def test_speaking_node_phase_guard(game_state, mock_emitter):
    # game_state starts at INIT phase by default
    agents = {}
    with pytest.raises(ValueError, match="speaking_node requires Phase.SPEAKING"):
        await speaking_node(game_state, agents, mock_emitter)

    game_state.current_phase = Phase.VOTING
    with pytest.raises(ValueError, match="speaking_node requires Phase.SPEAKING"):
        await speaking_node(game_state, agents, mock_emitter)


@pytest.mark.asyncio
async def test_speaking_node_sequential_context_injection(speaking_state, mock_emitter):
    # Setup mock agents that succeed on 1st attempt
    agents = {
        "agent_0": MockAgent([ok_out("t0", "s0")]),
        "agent_1": MockAgent([ok_out("t1", "s1")]),
        "agent_2": MockAgent([ok_out("t2", "s2")]),
        "agent_3": MockAgent([ok_out("t3", "s3")]),
    }

    state = await speaking_node(speaking_state, agents, mock_emitter)

    # Check Alice (agent_0, 1st in turn_order): empty public history
    calls_0 = agents["agent_0"].speak_calls
    assert len(calls_0) == 1
    assert calls_0[0]["context"].public_history == []

    # Check Bob (agent_1, 2nd): has s0
    calls_1 = agents["agent_1"].speak_calls
    assert len(calls_1) == 1
    history_1 = calls_1[0]["context"].public_history
    assert len(history_1) == 1
    assert history_1[0].agent_id == "agent_0"
    assert history_1[0].content == "s0"

    # Check Charlie (agent_2, 3rd): has s0, s1
    calls_2 = agents["agent_2"].speak_calls
    assert len(calls_2) == 1
    history_2 = calls_2[0]["context"].public_history
    assert len(history_2) == 2
    assert history_2[0].agent_id == "agent_0"
    assert history_2[1].agent_id == "agent_1"

    # Check Diana (agent_3, 4th): has s0, s1, s2
    calls_3 = agents["agent_3"].speak_calls
    assert len(calls_3) == 1
    history_3 = calls_3[0]["context"].public_history
    assert len(history_3) == 3
    assert [m.agent_id for m in history_3] == ["agent_0", "agent_1", "agent_2"]

    # Verify attributes of public history messages
    for msg in history_3:
        assert msg.phase == Phase.SPEAKING
        assert msg.round_number == state.current_round
        assert msg.deliberation_round is None


@pytest.mark.asyncio
async def test_speaking_node_gamestate_mutation(speaking_state, mock_emitter):
    agents = {
        "agent_0": MockAgent([ok_out("t0", "s0")]),
        "agent_1": MockAgent([ok_out("t1", "s1")]),
        "agent_2": MockAgent([ok_out("t2", "s2")]),
        "agent_3": MockAgent([ok_out("t3", "s3")]),
    }

    state = await speaking_node(speaking_state, agents, mock_emitter)

    assert len(state.all_messages) == 4
    for i, msg in enumerate(state.all_messages):
        assert msg.agent_id == f"agent_{i}"
        assert msg.phase == Phase.SPEAKING
        assert msg.round_number == state.current_round
        assert msg.content == f"s{i}"
        assert msg.deliberation_round is None
        assert msg.display_name == state.config.agents[i].display_name


@pytest.mark.asyncio
async def test_speaking_node_three_agents_scenario(speaking_state, mock_emitter):
    # Simulates round 2 where agent_1 is eliminated (dead)
    speaking_state.agent_alive["agent_1"] = False
    speaking_state.current_turn_order = ["agent_0", "agent_2", "agent_3"]
    speaking_state.current_round = 2

    agents = {
        "agent_0": MockAgent([ok_out("t0", "s0")]),
        "agent_2": MockAgent([ok_out("t2", "s2")]),
        "agent_3": MockAgent([ok_out("t3", "s3")]),
    }

    state = await speaking_node(speaking_state, agents, mock_emitter)

    assert len(state.all_messages) == 3
    assert [m.agent_id for m in state.all_messages] == ["agent_0", "agent_2", "agent_3"]
    for msg in state.all_messages:
        assert msg.round_number == 2


@pytest.mark.asyncio
async def test_speaking_node_returns_same_gamestate_reference(
    speaking_state, mock_emitter
):
    agents = {
        "agent_0": MockAgent([ok_out("t0", "s0")]),
        "agent_1": MockAgent([ok_out("t1", "s1")]),
        "agent_2": MockAgent([ok_out("t2", "s2")]),
        "agent_3": MockAgent([ok_out("t3", "s3")]),
    }

    ret_state = await speaking_node(speaking_state, agents, mock_emitter)
    assert ret_state is speaking_state


@pytest.mark.asyncio
async def test_speaking_node_is_final_round_injection(speaking_state, mock_emitter):
    agents = {
        "agent_0": MockAgent([ok_out("t0", "s0")]),
        "agent_1": MockAgent([ok_out("t1", "s1")]),
        "agent_2": MockAgent([ok_out("t2", "s2")]),
        "agent_3": MockAgent([ok_out("t3", "s3")]),
    }

    await speaking_node(speaking_state, agents, mock_emitter, is_final_round=True)

    for agent_id in speaking_state.current_turn_order:
        calls = agents[agent_id].speak_calls
        assert calls[0]["context"].is_final_round is True


def test_is_valid_speaking_output_helper():
    valid = ok_out("thinking", "hello")
    assert _is_valid_speaking_output(valid) is True

    # Empty values
    assert _is_valid_speaking_output(ok_out("", "hello")) is False
    assert _is_valid_speaking_output(ok_out("thinking", "")) is False
    assert _is_valid_speaking_output(ok_out(" ", " ")) is False

    # Non-SpeakingOutput types
    assert _is_valid_speaking_output(None) is False
    assert _is_valid_speaking_output("SpeakingOutput") is False


# --- Retry logic tests ---


@pytest.mark.asyncio
async def test_speak_retry_success_first_attempt(speaking_state, mock_emitter):
    agents = {
        "agent_0": MockAgent([ok_out("thought", "statement")]),
        "agent_1": MockAgent([ok_out("t1", "s1")]),
        "agent_2": MockAgent([ok_out("t2", "s2")]),
        "agent_3": MockAgent([ok_out("t3", "s3")]),
    }

    await speaking_node(speaking_state, agents, mock_emitter)
    assert len(agents["agent_0"].speak_calls) == 1


@pytest.mark.asyncio
async def test_speak_retry_success_second_attempt_exception(
    speaking_state, mock_emitter
):
    agents = {
        "agent_0": MockAgent(
            [
                ValueError("Connection Timeout"),
                ok_out("thought", "statement"),
            ]
        ),
        "agent_1": MockAgent([ok_out("t1", "s1")]),
        "agent_2": MockAgent([ok_out("t2", "s2")]),
        "agent_3": MockAgent([ok_out("t3", "s3")]),
    }

    await speaking_node(speaking_state, agents, mock_emitter)
    assert len(agents["agent_0"].speak_calls) == 2


@pytest.mark.asyncio
async def test_speak_retry_success_second_attempt_empty_output(
    speaking_state, mock_emitter
):
    agents = {
        "agent_0": MockAgent(
            [
                ok_out("", "invalid"),
                ok_out("thought", "statement"),
            ]
        ),
        "agent_1": MockAgent([ok_out("t1", "s1")]),
        "agent_2": MockAgent([ok_out("t2", "s2")]),
        "agent_3": MockAgent([ok_out("t3", "s3")]),
    }

    await speaking_node(speaking_state, agents, mock_emitter)
    assert len(agents["agent_0"].speak_calls) == 2


@pytest.mark.asyncio
async def test_speak_retry_failure_both_attempts_exception(
    speaking_state, mock_emitter
):
    agents = {
        "agent_0": MockAgent(
            [
                ValueError("Connection Timeout 1"),
                ValueError("Connection Timeout 2"),
            ]
        ),
        "agent_1": MockAgent([ok_out("t1", "s1")]),
        "agent_2": MockAgent([ok_out("t2", "s2")]),
        "agent_3": MockAgent([ok_out("t3", "s3")]),
    }

    with pytest.raises(AgentOutputError) as exc_info:
        await speaking_node(speaking_state, agents, mock_emitter)

    assert exc_info.value.agent_id == "agent_0"
    assert exc_info.value.phase == "speaking"
    assert exc_info.value.episode_id == speaking_state.episode_id
    assert "Connection Timeout 2" in str(exc_info.value)
    assert len(agents["agent_0"].speak_calls) == 2


@pytest.mark.asyncio
async def test_speak_retry_failure_both_attempts_invalid_output(
    speaking_state, mock_emitter
):
    agents = {
        "agent_0": MockAgent(
            [
                ok_out("", "s"),
                ok_out("t", " "),
            ]
        ),
        "agent_1": MockAgent([ok_out("t1", "s1")]),
        "agent_2": MockAgent([ok_out("t2", "s2")]),
        "agent_3": MockAgent([ok_out("t3", "s3")]),
    }

    with pytest.raises(AgentOutputError) as exc_info:
        await speaking_node(speaking_state, agents, mock_emitter)

    assert exc_info.value.agent_id == "agent_0"
    assert exc_info.value.phase == "speaking"
    assert len(agents["agent_0"].speak_calls) == 2


@pytest.mark.asyncio
async def test_speak_retry_one_failed_agent_stops_subsequent(
    speaking_state, mock_emitter
):
    agents = {
        "agent_0": MockAgent([ok_out("t0", "s0")]),
        "agent_1": MockAgent(
            [
                ValueError("Connection Timeout 1"),
                ValueError("Connection Timeout 2"),
            ]
        ),
        "agent_2": MockAgent([ok_out("t2", "s2")]),
        "agent_3": MockAgent([ok_out("t3", "s3")]),
    }

    with pytest.raises(AgentOutputError):
        await speaking_node(speaking_state, agents, mock_emitter)

    # agent_0 should have spoken successfully
    assert len(agents["agent_0"].speak_calls) == 1
    assert len(speaking_state.all_messages) == 1
    assert speaking_state.all_messages[0].agent_id == "agent_0"

    # agent_1 failed
    assert len(agents["agent_1"].speak_calls) == 2

    # agent_2 and agent_3 should not have been called
    assert len(agents["agent_2"].speak_calls) == 0
    assert len(agents["agent_3"].speak_calls) == 0


# --- Event emission integration tests (S3) ---


@pytest.mark.asyncio
async def test_speaking_node_event_emission_integration(
    speaking_state, fake_redis, fake_redis_client
):
    emitter = EventEmitter(fake_redis_client, speaking_state.episode_id)

    pubsub = fake_redis.pubsub()
    await pubsub.subscribe(emitter.channel)
    await asyncio.sleep(0.01)

    agents = {
        "agent_0": MockAgent([ok_out("t0", "s0")]),
        "agent_1": MockAgent([ok_out("t1", "s1")]),
        "agent_2": MockAgent([ok_out("t2", "s2")]),
        "agent_3": MockAgent([ok_out("t3", "s3")]),
    }

    await speaking_node(speaking_state, agents, emitter)

    # Listen to the 5 expected events
    events = []
    async for m in pubsub.listen():
        if m["type"] == "message":
            events.append(json.loads(m["data"].decode("utf-8")))
            if len(events) == 5:
                break

    assert len(events) == 5

    # 1. Verify ROUND_STARTED event
    event_start = events[0]
    assert event_start["event_type"] == EVT_ROUND_STARTED
    assert event_start["episode_id"] == speaking_state.episode_id
    assert event_start["payload"]["round_number"] == speaking_state.current_round
    assert event_start["payload"]["turn_order"] == speaking_state.current_turn_order

    # 2. Verify 4 AGENT_SPOKE events in turn_order sequence
    for idx, agent_id in enumerate(speaking_state.current_turn_order):
        event_spoke = events[idx + 1]
        assert event_spoke["event_type"] == EVT_AGENT_SPOKE
        assert event_spoke["episode_id"] == speaking_state.episode_id

        payload = event_spoke["payload"]
        agent_config = next(
            a for a in speaking_state.config.agents if a.agent_id == agent_id
        )
        assert payload["agent_id"] == agent_id
        assert payload["display_name"] == agent_config.display_name
        assert payload["public_statement"] == f"s{agent_id[-1]}"
        assert payload["phase"] == Phase.SPEAKING
        assert payload["round_number"] == speaking_state.current_round

        # Privacy guard check
        assert "inner_thought" not in payload
        assert "t0" not in json.dumps(event_spoke)
        assert "t1" not in json.dumps(event_spoke)
