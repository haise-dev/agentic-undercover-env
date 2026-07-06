import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import fakeredis
import pytest

from src.core.redis import RedisClient
from src.engine.event_emitter import EVT_GAME_START, EventEmitter
from src.engine.nodes.init_node import _build_game_start_payload, init_node
from src.models import Phase, Role


# --- Mock EventEmitter fixture ---
@pytest.fixture
def mock_emitter():
    emitter = MagicMock(spec=EventEmitter)
    emitter.emit = AsyncMock()
    return emitter


@pytest.mark.asyncio
async def test_init_node_role_assignments(episode_config, mock_emitter):
    state = await init_node(episode_config, mock_emitter)

    # Validate roles
    imposter_count = 0
    villager_count = 0
    for assignment in state.role_assignments.values():
        if assignment.role == Role.IMPOSTER:
            imposter_count += 1
            assert assignment.secret_word is None
        elif assignment.role == Role.VILLAGER:
            villager_count += 1
            assert assignment.secret_word == episode_config.secret_word
        assert assignment.topic == episode_config.topic

    assert imposter_count == 1
    assert villager_count == 3


@pytest.mark.asyncio
async def test_init_node_role_assignments_statistical(episode_config, mock_emitter):
    imposter_counts = {agent.agent_id: 0 for agent in episode_config.agents}
    
    for _ in range(1000):
        state = await init_node(episode_config, mock_emitter)
        imposter_id = state.imposter_id
        imposter_counts[imposter_id] += 1

    # Verify every agent was imposter at least once
    for agent_id, count in imposter_counts.items():
        assert count > 0, (
            f"Agent {agent_id} was never selected as Imposter in 1000 runs"
        )
    
    # Total selected must be 1000
    assert sum(imposter_counts.values()) == 1000


@pytest.mark.asyncio
async def test_init_node_turn_order(episode_config, mock_emitter):
    state = await init_node(episode_config, mock_emitter)
    agent_ids = [agent.agent_id for agent in episode_config.agents]

    assert len(state.current_turn_order) == 4
    assert set(state.current_turn_order) == set(agent_ids)


@pytest.mark.asyncio
async def test_init_node_turn_order_randomness_statistical(
    episode_config, mock_emitter
):
    orders = set()
    for _ in range(100):
        state = await init_node(episode_config, mock_emitter)
        orders.add(tuple(state.current_turn_order))

    # With 100 runs, there should be multiple distinct turn orders
    # (total permutations is 24)
    assert len(orders) > 1


@pytest.mark.asyncio
async def test_init_node_gamestate_fields(episode_config, mock_emitter):
    state = await init_node(episode_config, mock_emitter)

    assert state.episode_id == episode_config.episode_id
    assert state.current_phase == Phase.INIT
    assert state.current_round == 1
    assert state.current_deliberation_round == 1
    assert state.agent_alive == {
        "agent_0": True,
        "agent_1": True,
        "agent_2": True,
        "agent_3": True,
    }
    assert state.all_messages == []
    assert state.all_announcements == []
    assert state.poll_history == {}
    assert state.vote_records == []
    assert state.elimination_result is None
    assert state.result is None
    assert state.ended_at is None
    
    # Verify timestamp format
    dt = datetime.fromisoformat(state.started_at)
    assert dt is not None
    assert "+00:00" in state.started_at or state.started_at.endswith("Z")


def test_build_game_start_payload(episode_config, role_assignments):
    turn_order = ["agent_3", "agent_1", "agent_0", "agent_2"]
    payload = _build_game_start_payload(episode_config, turn_order, role_assignments)

    assert payload["episode_id"] == episode_config.episode_id
    assert payload["topic"] == episode_config.topic
    assert payload["topic"] != episode_config.secret_word
    assert payload["turn_order"] == turn_order

    payload_str = json.dumps(payload)
    # Observer needs to see the roles and secret word
    assert episode_config.secret_word in payload_str
    assert "imposter" in payload_str.lower()
    assert "villager" in payload_str.lower()

    assert len(payload["agents"]) == 4
    for _i, agent in enumerate(payload["agents"]):
        assert "agent_id" in agent
        assert "display_name" in agent
        assert "display_color" in agent
        assert "agent_type" in agent
        assert "role" in agent
        assert "secret_word" in agent


# --- Event emission integration tests (S2) ---


@pytest.mark.asyncio
async def test_init_node_event_emission_integration(
    episode_config, fake_redis, fake_redis_client
):
    emitter = EventEmitter(fake_redis_client, episode_config.episode_id)

    pubsub = fake_redis.pubsub()
    await pubsub.subscribe(emitter.channel)
    await asyncio.sleep(0.01)

    state = await init_node(episode_config, emitter)

    # Retrieve emitted message
    msg = None
    async for m in pubsub.listen():
        if m["type"] == "message":
            msg = m
            break

    assert msg is not None
    envelope = json.loads(msg["data"].decode("utf-8"))

    # Validate envelope
    assert envelope["event_type"] == EVT_GAME_START
    assert envelope["episode_id"] == episode_config.episode_id
    assert "timestamp" in envelope
    
    # Validate payload
    payload = envelope["payload"]
    assert payload["episode_id"] == episode_config.episode_id
    assert payload["topic"] == episode_config.topic
    assert payload["turn_order"] == state.current_turn_order

    # Validate payload has observer info
    envelope_str = json.dumps(envelope)
    assert episode_config.secret_word in envelope_str
    assert "imposter" in envelope_str.lower()
    assert "villager" in envelope_str.lower()
