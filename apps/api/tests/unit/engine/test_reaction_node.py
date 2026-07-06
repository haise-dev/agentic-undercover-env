import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.engine.event_emitter import (
    EVT_LAST_WORDS,
    EVT_ROLE_REVEAL,
    EVT_SURVIVOR_REACTED,
    EventEmitter,
)
from src.engine.exceptions import NodeError
from src.engine.nodes.reaction_node import reaction_node
from src.models import EliminationResult, Phase, ReactionOutput
from tests.unit.engine.conftest import MockAgent


# --- Mock EventEmitter fixture ---
@pytest.fixture
def mock_emitter():
    emitter = MagicMock(spec=EventEmitter)
    emitter.emit = AsyncMock()
    return emitter


# --- Helper to create game state in reaction phase ---
@pytest.fixture
def reaction_state(game_state):
    game_state.current_phase = Phase.REACTION
    # Needs elimination result to be valid
    game_state.elimination_result = EliminationResult(
        eliminated_agent_id="agent_1",
        vote_tally={"agent_1": 3, "agent_2": 1},
        was_tiebreak=False,
        tiebreak_candidates=None,
    )
    # The eliminated agent should be dead
    game_state.agent_alive["agent_1"] = False
    return game_state


def ok_react(statement: str, thought: str = "think") -> ReactionOutput:
    return ReactionOutput(inner_thought=thought, public_statement=statement)


@pytest.mark.asyncio
async def test_reaction_node_phase_guard(game_state, mock_emitter):
    agents = {}
    with pytest.raises(ValueError, match="reaction_node requires Phase.REACTION"):
        await reaction_node(game_state, agents, mock_emitter)


@pytest.mark.asyncio
async def test_reaction_node_requires_elimination_result(game_state, mock_emitter):
    game_state.current_phase = Phase.REACTION
    game_state.elimination_result = None
    agents = {}
    with pytest.raises(NodeError, match="requires elimination_result to be populated"):
        await reaction_node(game_state, agents, mock_emitter)


@pytest.mark.asyncio
async def test_reaction_node_happy_path(reaction_state, mock_emitter):
    agents = {
        "agent_0": MockAgent(react_outputs=[ok_react("Surv 0 react")]),
        "agent_1": MockAgent(react_outputs=[ok_react("My last words")]),
        "agent_2": MockAgent(react_outputs=[ok_react("Surv 2 react")]),
        "agent_3": MockAgent(react_outputs=[ok_react("Surv 3 react")]),
    }

    state = await reaction_node(reaction_state, agents, mock_emitter)

    # 1 last words + 3 survivor reactions = 4 messages appended
    # Also 1 announcement appended
    assert len(state.all_messages) == 4
    assert len(state.all_announcements) == 1

    # First message should be last words
    assert state.all_messages[0].agent_id == "agent_1"
    assert state.all_messages[0].content == "My last words"
    assert state.all_messages[0].phase == Phase.REACTION

    # The announcement should be correct
    ann = state.all_announcements[0]
    assert ann.phase == Phase.REACTION
    assert "[SYSTEM] The eliminated agent (agent_1) was" in ann.content

    # The next 3 messages should be the survivors (in shuffled order)
    survivor_messages = state.all_messages[1:]
    assert len(survivor_messages) == 3
    survivor_ids = {m.agent_id for m in survivor_messages}
    assert survivor_ids == {"agent_0", "agent_2", "agent_3"}


@pytest.mark.asyncio
async def test_reaction_node_retry_logic(reaction_state, mock_emitter):
    agents = {
        "agent_0": MockAgent(
            react_outputs=[ValueError("Fail 1"), ok_react("Surv 0 ok")]
        ),
        "agent_1": MockAgent(react_outputs=[ValueError("Fail 1"), ok_react("Last ok")]),
        "agent_2": MockAgent(react_outputs=[ok_react("Surv 2 ok")]),
        "agent_3": MockAgent(react_outputs=[ok_react("Surv 3 ok")]),
    }

    state = await reaction_node(reaction_state, agents, mock_emitter)

    assert state.all_messages[0].agent_id == "agent_1"
    assert state.all_messages[0].content == "Last ok"

    survivor_msgs = {m.agent_id: m.content for m in state.all_messages[1:]}
    assert survivor_msgs["agent_0"] == "Surv 0 ok"


@pytest.mark.asyncio
async def test_reaction_node_fallback_logic(reaction_state, mock_emitter):
    agents = {
        "agent_0": MockAgent(
            react_outputs=[ValueError("Fail 1"), ValueError("Fail 2")]
        ),
        "agent_1": MockAgent(
            react_outputs=[ValueError("Fail 1"), ValueError("Fail 2")]
        ),
        "agent_2": MockAgent(react_outputs=[ok_react("Surv 2 ok")]),
        "agent_3": MockAgent(react_outputs=[ok_react("Surv 3 ok")]),
    }

    state = await reaction_node(reaction_state, agents, mock_emitter)

    # Last words fallback
    assert state.all_messages[0].agent_id == "agent_1"
    assert state.all_messages[0].content == "*remains silent as they are dragged away*"

    # Survivor fallback
    survivor_msgs = {m.agent_id: m.content for m in state.all_messages[1:]}
    assert survivor_msgs["agent_0"] == "*looks shocked and stays silent*"


@pytest.mark.asyncio
async def test_reaction_node_concurrency(reaction_state, mock_emitter):
    # Setup mock agents where each survivor agent sleeps for 50ms inside react()
    class SlowReactAgent:
        async def react(self, context):
            await asyncio.sleep(0.05)
            return ok_react("Slow reaction")

    class FastReactAgent:
        async def react(self, context):
            return ok_react("Fast reaction")

    agents = {
        "agent_0": SlowReactAgent(),
        # Eliminated agent is sequential, so don't make it slow for the test
        "agent_1": FastReactAgent(),
        "agent_2": SlowReactAgent(),
        "agent_3": SlowReactAgent(),
    }

    start_time = time.perf_counter()
    await reaction_node(reaction_state, agents, mock_emitter)
    duration = time.perf_counter() - start_time

    # 3 survivors sleeping 50ms concurrently should be < 150ms
    # If sequential, it would be >= 150ms.
    assert duration < 0.14


@pytest.mark.asyncio
async def test_reaction_node_shuffle_uniformity(reaction_state, mock_emitter):
    # Verify that the survivor reactions are appended in a randomized order
    first_reactors = set()

    for _ in range(100):
        # We don't need fully fresh state as long as we clear all_messages
        reaction_state.all_messages.clear()

        agents = {
            "agent_0": MockAgent(react_outputs=[ok_react("0")]),
            "agent_1": MockAgent(react_outputs=[ok_react("1")]),
            "agent_2": MockAgent(react_outputs=[ok_react("2")]),
            "agent_3": MockAgent(react_outputs=[ok_react("3")]),
        }

        ret_state = await reaction_node(reaction_state, agents, mock_emitter)

        # [0] is eliminated agent. [1] is the first survivor to react.
        first_survivor_msg = ret_state.all_messages[1]
        first_reactors.add(first_survivor_msg.agent_id)

    # With 100 runs, all 3 survivors should have been first at least once
    assert first_reactors == {"agent_0", "agent_2", "agent_3"}


@pytest.mark.asyncio
async def test_reaction_node_event_emission_integration(
    reaction_state, fake_redis, fake_redis_client
):
    emitter = EventEmitter(fake_redis_client, reaction_state.episode_id)

    pubsub = fake_redis.pubsub()
    await pubsub.subscribe(emitter.channel)
    await asyncio.sleep(0.01)

    agents = {
        "agent_0": MockAgent(react_outputs=[ok_react("Surv 0 react", "t0")]),
        "agent_1": MockAgent(react_outputs=[ok_react("My last words", "t1")]),
        "agent_2": MockAgent(react_outputs=[ok_react("Surv 2 react", "t2")]),
        "agent_3": MockAgent(react_outputs=[ok_react("Surv 3 react", "t3")]),
    }

    await reaction_node(reaction_state, agents, emitter)

    # Retrieve all 5 events (1 last words, 1 reveal, 3 survivor reactions)
    events = []
    async for m in pubsub.listen():
        if m["type"] == "message":
            events.append(json.loads(m["data"].decode("utf-8")))
            if len(events) == 5:
                break

    assert len(events) == 5

    # Event 1: LAST_WORDS
    assert events[0]["event_type"] == EVT_LAST_WORDS
    assert events[0]["payload"]["agent_id"] == "agent_1"
    assert events[0]["payload"]["statement"] == "My last words"
    assert "t1" not in json.dumps(events[0])

    # Event 2: ROLE_REVEAL
    assert events[1]["event_type"] == EVT_ROLE_REVEAL
    assert events[1]["payload"]["agent_id"] == "agent_1"
    assert "role" in events[1]["payload"]

    # Events 3, 4, 5: SURVIVOR_REACTED
    survivor_event_agents = set()
    for i in range(2, 5):
        assert events[i]["event_type"] == EVT_SURVIVOR_REACTED
        survivor_event_agents.add(events[i]["payload"]["agent_id"])
        assert "t0" not in json.dumps(events[i])
        assert "t2" not in json.dumps(events[i])
        assert "t3" not in json.dumps(events[i])

    assert survivor_event_agents == {"agent_0", "agent_2", "agent_3"}
