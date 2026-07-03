import asyncio
import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
import fakeredis
from unittest.mock import patch

from src.core.redis import get_redis_client, RedisClient


@pytest.fixture
def fake_redis_client():
    """Fixture that patches Redis to use FakeAsyncRedis for integration testing."""
    fake_redis = fakeredis.FakeAsyncRedis()
    with patch("redis.asyncio.Redis", return_value=fake_redis):
        yield fake_redis


@pytest.mark.asyncio
async def test_publish_subscribe_roundtrip(fake_redis_client):
    """[S3-T1] E2E round-trip publish and subscribe message validation."""
    test_data = {"event": "ROUND_END", "data": {"winner": "imposter"}}

    async with get_redis_client() as client:
        async def run_sub():
            async for msg in client.subscribe("game:123"):
                return msg

        sub_task = asyncio.create_task(run_sub())
        await asyncio.sleep(0.05)  # Let subscription set up

        # Publish should return count of active subscribers
        subs = await client.publish("game:123", test_data)
        assert subs == 1

        received = await sub_task
        assert received == test_data


@pytest.mark.asyncio
async def test_publish_returns_subscriber_count(fake_redis_client):
    """[S3-T2] publish returns correct subscriber count based on active subscribers."""
    async with get_redis_client() as client:
        # Publish with no subscribers
        count = await client.publish("chan1", {"status": "ok"})
        assert count == 0

        # Subscribe 1
        async def run_sub1():
            async for msg in client.subscribe("chan1"):
                return msg

        # Subscribe 2
        async def run_sub2():
            async for msg in client.subscribe("chan1"):
                return msg

        task1 = asyncio.create_task(run_sub1())
        task2 = asyncio.create_task(run_sub2())
        await asyncio.sleep(0.05)

        # Publish with 2 subscribers
        subs = await client.publish("chan1", {"status": "ok"})
        assert subs == 2

        await task1
        await task2


@pytest.mark.asyncio
async def test_get_set_roundtrip(fake_redis_client):
    """[S3-T3] get/set round-trip retrieves correct key value."""
    async with get_redis_client() as client:
        await client.set("key", "value")
        val = await client.get("key")
        assert val == "value"


@pytest.mark.asyncio
async def test_get_nonexistent_key(fake_redis_client):
    """[S3-T4] get nonexistent key returns None."""
    async with get_redis_client() as client:
        val = await client.get("missing_key_123")
        assert val is None


@pytest.mark.asyncio
async def test_delete_key(fake_redis_client):
    """[S3-T5] delete removes the key and returns count of deleted keys."""
    async with get_redis_client() as client:
        await client.set("key_to_del", "val")
        
        # Verify it exists
        assert await client.get("key_to_del") == "val"
        
        # Delete and check count
        deleted_count = await client.delete("key_to_del")
        assert deleted_count == 1
        
        # Get should now return None
        assert await client.get("key_to_del") is None


@pytest.mark.asyncio
async def test_ping_healthy_client(fake_redis_client):
    """[S3-T6] ping returns True on healthy client."""
    async with get_redis_client() as client:
        ok = await client.ping()
        assert ok is True


@pytest.mark.asyncio
async def test_subscribe_multiple_messages(fake_redis_client):
    """[S3-T7] subscribe yields multiple messages sequentially in correct order."""
    async with get_redis_client() as client:
        async def run_subscriber():
            messages = []
            async for msg in client.subscribe("chan_seq"):
                messages.append(msg)
                if len(messages) == 3:
                    break
            return messages

        sub_task = asyncio.create_task(run_subscriber())
        await asyncio.sleep(0.05)

        await client.publish("chan_seq", {"msg": "first"})
        await client.publish("chan_seq", {"msg": "second"})
        await client.publish("chan_seq", {"msg": "third"})

        received = await sub_task
        assert received == [
            {"msg": "first"},
            {"msg": "second"},
            {"msg": "third"},
        ]
