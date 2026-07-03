import asyncio
import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis
import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from src.core.redis import (
    RedisClient,
    check_redis_connection,
    create_redis_pool,
    get_redis_client,
)

logger = logging.getLogger(__name__)


# ── S1 UNIT TESTS ─────────────────────────────────────────────────────

def test_create_redis_pool_valid():
    """[S1-T1] create_redis_pool() with valid URL creates pool with correct max_connections."""
    pool = create_redis_pool("redis://localhost:6379/0", max_connections=10)
    assert pool is not None
    assert pool.connection_class.__name__ == "Connection"
    assert pool.max_connections == 10


def test_create_redis_pool_invalid():
    """[S1-T2] create_redis_pool() with invalid URL scheme raises ValueError."""
    with pytest.raises(ValueError, match="Invalid Redis URL scheme"):
        create_redis_pool("http://localhost:6379")


@pytest.mark.asyncio
async def test_check_redis_connection_success(caplog):
    """[S1-T3] check_redis_connection() succeeds on first attempt and logs connection status."""
    mock_client = AsyncMock()
    mock_client.ping.return_value = True

    with caplog.at_level(logging.INFO):
        await check_redis_connection(mock_client, retries=(0.1,))

    assert mock_client.ping.call_count == 1
    assert "Redis connection verified successfully" in caplog.text


@pytest.mark.asyncio
async def test_check_redis_connection_retry_success(caplog):
    """[S1-T4] check_redis_connection() fails initially but succeeds on retry."""
    mock_client = AsyncMock()
    # First 2 calls raise ConnectionError, 3rd succeeds
    mock_client.ping.side_effect = [
        RedisConnectionError("Connection refused"),
        RedisConnectionError("Connection refused"),
        True,
    ]

    with caplog.at_level(logging.DEBUG):
        await check_redis_connection(mock_client, retries=(0.01, 0.02))

    assert mock_client.ping.call_count == 3
    assert "Redis connection verified successfully" in caplog.text


@pytest.mark.asyncio
async def test_check_redis_connection_all_retries_fail():
    """[S1-T5] check_redis_connection() raises RedisConnectionError when all retries are exhausted."""
    mock_client = MagicMock()
    mock_client.ping = AsyncMock(side_effect=RedisConnectionError("Connection refused"))

    with pytest.raises(RedisConnectionError, match="Failed to connect to Redis after 3 attempts"):
        await check_redis_connection(mock_client, retries=(0.01, 0.02))

    assert mock_client.ping.call_count == 3


@pytest.mark.asyncio
async def test_get_redis_client_success():
    """[S1-T6] get_redis_client() yields a RedisClient wrapper on successful connection."""
    fake_redis = fakeredis.FakeAsyncRedis()
    
    # We patch the underlying redis.asyncio.Redis call inside the context manager
    with patch("redis.asyncio.Redis", return_value=fake_redis):
        async with get_redis_client("redis://localhost:6379/0") as client:
            assert isinstance(client, RedisClient)
            assert client.raw is fake_redis
            assert await client.ping() is True


@pytest.mark.asyncio
async def test_get_redis_client_connection_error():
    """[S1-T7] get_redis_client() raises RedisConnectionError when connection fails."""
    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(side_effect=RedisConnectionError("Refused"))
    mock_redis.aclose = AsyncMock()

    with patch("redis.asyncio.Redis", return_value=mock_redis):
        with pytest.raises(RedisConnectionError, match="Failed to connect to Redis"):
            async with get_redis_client("redis://localhost:6379/0", retries=(0.001,)) as _:
                pass


@pytest.mark.asyncio
async def test_redis_client_ping_healthy():
    """[S1-T8] RedisClient.ping() returns True when Redis is healthy."""
    fake_redis = fakeredis.FakeAsyncRedis()
    client = RedisClient(fake_redis)
    assert await client.ping() is True


@pytest.mark.asyncio
async def test_redis_client_ping_down():
    """[S1-T9] RedisClient.ping() returns False (never raises) when Redis is down."""
    mock_redis = AsyncMock()
    mock_redis.ping.side_effect = RedisConnectionError("Refused")
    client = RedisClient(mock_redis)
    assert await client.ping() is False


@pytest.mark.asyncio
async def test_redis_client_get_existing():
    """[S1-T10] RedisClient.get() returns string value for existing key."""
    fake_redis = fakeredis.FakeAsyncRedis()
    await fake_redis.set("name", "aue")
    client = RedisClient(fake_redis)
    assert await client.get("name") == "aue"


@pytest.mark.asyncio
async def test_redis_client_get_missing():
    """[S1-T11] RedisClient.get() returns None for missing key."""
    fake_redis = fakeredis.FakeAsyncRedis()
    client = RedisClient(fake_redis)
    assert await client.get("missing_key") is None


@pytest.mark.asyncio
async def test_redis_client_set_no_ttl():
    """[S1-T12] RedisClient.set() sets key value indefinitely."""
    fake_redis = fakeredis.FakeAsyncRedis()
    client = RedisClient(fake_redis)
    await client.set("key", "val")
    assert await fake_redis.get("key") == b"val"
    assert await fake_redis.ttl("key") == -1  # no expiry


@pytest.mark.asyncio
async def test_redis_client_set_with_ttl():
    """[S1-T13] RedisClient.set() sets key with TTL."""
    fake_redis = fakeredis.FakeAsyncRedis()
    client = RedisClient(fake_redis)
    await client.set("key", "val", ex=5)
    assert await fake_redis.get("key") == b"val"
    ttl = await fake_redis.ttl("key")
    assert 0 < ttl <= 5


@pytest.mark.asyncio
async def test_redis_client_delete_existing():
    """[S1-T14] RedisClient.delete() deletes existing key and returns 1."""
    fake_redis = fakeredis.FakeAsyncRedis()
    await fake_redis.set("key1", "val1")
    client = RedisClient(fake_redis)
    deleted = await client.delete("key1")
    assert deleted == 1
    assert await fake_redis.get("key1") is None


@pytest.mark.asyncio
async def test_redis_client_delete_nonexistent():
    """[S1-T15] RedisClient.delete() returns 0 for nonexistent keys."""
    fake_redis = fakeredis.FakeAsyncRedis()
    client = RedisClient(fake_redis)
    deleted = await client.delete("nonexistent")
    assert deleted == 0


# ── S2 UNIT TESTS ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_publish_valid_dict():
    """[S2-T1] publish() with valid dict publishes payload and returns subscriber count."""
    fake_redis = fakeredis.FakeAsyncRedis()
    client = RedisClient(fake_redis)
    
    # Publish without subscribers returns 0
    count = await client.publish("chan1", {"status": "ok"})
    assert count == 0


@pytest.mark.asyncio
async def test_publish_invalid_payload():
    """[S2-T2] publish() with non-serializable payload raises ValueError."""
    fake_redis = fakeredis.FakeAsyncRedis()
    client = RedisClient(fake_redis)
    
    class NonSerializable:
        pass
        
    with pytest.raises(ValueError, match="Message must be JSON-serializable"):
        await client.publish("chan1", {"data": NonSerializable()})


@pytest.mark.asyncio
async def test_publish_empty_dict():
    """[S2-T3] publish() with empty dict publishes successfully."""
    fake_redis = fakeredis.FakeAsyncRedis()
    client = RedisClient(fake_redis)
    count = await client.publish("chan1", {})
    assert count == 0


@pytest.mark.asyncio
async def test_publish_nested_dict():
    """[S2-T4] publish() preserves nested structures."""
    fake_redis = fakeredis.FakeAsyncRedis()
    client = RedisClient(fake_redis)
    payload = {"a": {"b": [1, 2, 3]}}
    
    # We can check raw publish in Redis
    pubsub = fake_redis.pubsub()
    await pubsub.subscribe("chan_nested")
    
    await client.publish("chan_nested", payload)
    
    # Read messages
    msg1 = await pubsub.get_message()  # subscribe control message
    assert msg1["type"] == "subscribe"
    
    msg2 = await pubsub.get_message()  # published message
    assert msg2["type"] == "message"
    decoded = json.loads(msg2["data"].decode("utf-8"))
    assert decoded == payload
    await pubsub.aclose()


@pytest.mark.asyncio
async def test_subscribe_published_message_received():
    """[S2-T5] subscribe() yields published message as decoded dict."""
    fake_redis = fakeredis.FakeAsyncRedis()
    client = RedisClient(fake_redis)
    payload = {"hello": "world"}

    # We need to run subscribe and publish concurrently
    async def run_subscriber():
        messages = []
        async for msg in client.subscribe("chan_sub"):
            messages.append(msg)
            break  # stop after receiving one message
        return messages

    # Start subscriber task
    sub_task = asyncio.create_task(run_subscriber())
    await asyncio.sleep(0.05)  # allow subscribe setup

    # Publish
    await client.publish("chan_sub", payload)
    
    received = await sub_task
    assert len(received) == 1
    assert received[0] == payload


@pytest.mark.asyncio
async def test_subscribe_multiple_messages():
    """[S2-T6] subscribe() yields multiple messages in order."""
    fake_redis = fakeredis.FakeAsyncRedis()
    client = RedisClient(fake_redis)

    async def run_subscriber():
        messages = []
        async for msg in client.subscribe("chan_multi"):
            messages.append(msg)
            if len(messages) == 3:
                break
        return messages

    sub_task = asyncio.create_task(run_subscriber())
    await asyncio.sleep(0.05)

    await client.publish("chan_multi", {"idx": 1})
    await client.publish("chan_multi", {"idx": 2})
    await client.publish("chan_multi", {"idx": 3})

    received = await sub_task
    assert received == [{"idx": 1}, {"idx": 2}, {"idx": 3}]


@pytest.mark.asyncio
async def test_subscribe_wrong_channel():
    """[S2-T7] subscribe() does not receive messages from other channels."""
    fake_redis = fakeredis.FakeAsyncRedis()
    client = RedisClient(fake_redis)

    async def run_subscriber():
        messages = []
        # timeout after 0.2 seconds since we shouldn't receive anything
        try:
            async with asyncio.timeout(0.2):
                async for msg in client.subscribe("chan_correct"):
                    messages.append(msg)
        except TimeoutError:
            pass
        return messages

    sub_task = asyncio.create_task(run_subscriber())
    await asyncio.sleep(0.05)

    await client.publish("chan_wrong", {"val": "ignored"})
    
    received = await sub_task
    assert len(received) == 0


@pytest.mark.asyncio
async def test_subscribe_invalid_json():
    """[S2-T8] subscribe() raises JSONDecodeError on non-JSON payload."""
    fake_redis = fakeredis.FakeAsyncRedis()
    client = RedisClient(fake_redis)

    async def run_subscriber():
        try:
            async for _ in client.subscribe("chan_bad_json"):
                pass
        except json.JSONDecodeError:
            return "json_error"
        return "no_error"

    sub_task = asyncio.create_task(run_subscriber())
    await asyncio.sleep(0.05)

    # Publish raw string instead of JSON dict using raw redis
    await fake_redis.publish("chan_bad_json", "not a json string")

    result = await sub_task
    assert result == "json_error"


@pytest.mark.asyncio
async def test_publish_subscribe_roundtrip_e2e():
    """[S2-T9] E2E round-trip publish and subscribe message validation."""
    fake_redis = fakeredis.FakeAsyncRedis()
    client = RedisClient(fake_redis)
    test_data = {"event": "ROUND_END", "data": {"winner": "imposter"}}

    async def run_sub():
        async for msg in client.subscribe("game:123"):
            return msg

    sub_task = asyncio.create_task(run_sub())
    await asyncio.sleep(0.05)

    # There should be 1 subscriber active
    subs = await client.publish("game:123", test_data)
    assert subs == 1

    received = await sub_task
    assert received == test_data
