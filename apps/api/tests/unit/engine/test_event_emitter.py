import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
import fakeredis
from redis.exceptions import ConnectionError as RedisConnectionError

from src.core.redis import RedisClient
from src.engine.event_emitter import (
    EventEmitter,
    EVT_GAME_START,
    EVT_AGENT_SPOKE,
)


@pytest.fixture
def fake_redis():
    """Returns a FakeAsyncRedis instance."""
    return fakeredis.FakeAsyncRedis()


@pytest.fixture
def redis_client(fake_redis):
    """Returns a RedisClient wrapping FakeAsyncRedis."""
    return RedisClient(fake_redis)


@pytest.mark.asyncio
async def test_event_emitter_channel(redis_client):
    emitter = EventEmitter(redis_client, "episode_123")
    assert emitter.channel == "episode:episode_123"


@pytest.mark.asyncio
async def test_event_emitter_emit_happy_path(fake_redis, redis_client):
    episode_id = "episode_123"
    emitter = EventEmitter(redis_client, episode_id)
    payload = {"some": "data", "nested": [1, 2, 3]}

    # Subscribe to channel using fake_redis directly or through pubsub
    pubsub = fake_redis.pubsub()
    await pubsub.subscribe(emitter.channel)

    # Let subscription setup
    await asyncio.sleep(0.01)

    await emitter.emit(EVT_GAME_START, payload)

    # Listen for the message
    msg = None
    async for m in pubsub.listen():
        if m["type"] == "message":
            msg = m
            break

    assert msg is not None
    data = json.loads(msg["data"].decode("utf-8"))

    assert data["event_type"] == EVT_GAME_START
    assert data["episode_id"] == episode_id
    assert data["payload"] == payload
    # Validate timestamp
    ts = datetime.fromisoformat(data["timestamp"])
    assert ts is not None


@pytest.mark.asyncio
async def test_event_emitter_emit_non_json_serializable(redis_client):
    emitter = EventEmitter(redis_client, "episode_123")
    # Objects are not JSON-serializable by default
    bad_payload = {"object": object()}

    with pytest.raises(ValueError) as exc_info:
        await emitter.emit(EVT_AGENT_SPOKE, bad_payload)
    
    assert "Payload must be JSON-serializable" in str(exc_info.value)


@pytest.mark.asyncio
async def test_event_emitter_redis_error(redis_client):
    # Mock redis_client.publish to raise RedisConnectionError
    mock_publish = AsyncMock(side_effect=RedisConnectionError("Connection lost"))
    
    with patch.object(redis_client, "publish", mock_publish):
        emitter = EventEmitter(redis_client, "episode_123")
        with pytest.raises(RedisConnectionError):
            await emitter.emit(EVT_GAME_START, {"status": "ok"})


@pytest.mark.asyncio
async def test_event_emitter_multiple_emits(fake_redis, redis_client):
    episode_id = "episode_456"
    emitter = EventEmitter(redis_client, episode_id)

    pubsub = fake_redis.pubsub()
    await pubsub.subscribe(emitter.channel)
    await asyncio.sleep(0.01)

    await emitter.emit(EVT_GAME_START, {"step": 1})
    await emitter.emit(EVT_AGENT_SPOKE, {"step": 2})

    messages = []
    async for m in pubsub.listen():
        if m["type"] == "message":
            messages.append(json.loads(m["data"].decode("utf-8")))
            if len(messages) == 2:
                break

    assert len(messages) == 2
    assert messages[0]["event_type"] == EVT_GAME_START
    assert messages[0]["payload"] == {"step": 1}
    assert messages[1]["event_type"] == EVT_AGENT_SPOKE
    assert messages[1]["payload"] == {"step": 2}
