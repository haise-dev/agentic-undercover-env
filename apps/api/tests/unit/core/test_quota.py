import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import fakeredis

from src.core.quota import QuotaTracker


@pytest.mark.asyncio
async def test_quota_tracker_redis_success():
    """Test that QuotaTracker successfully marks and checks quota status using Redis."""
    fake_redis = fakeredis.FakeAsyncRedis()
    
    # We patch get_redis_client to return our fake redis client
    class MockRedisContext:
        async def __aenter__(self):
            # We return a wrapper similar to RedisClient or just direct client
            # But get_redis_client returns a RedisClient wrapper! Let's mock that.
            from src.core.redis import RedisClient
            return RedisClient(fake_redis)
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("src.core.quota.get_redis_client", return_value=MockRedisContext()):
        # Ensure it starts as not exhausted
        assert await QuotaTracker.is_exhausted("gemini") is False
        
        # Mark exhausted with 1 second TTL
        await QuotaTracker.mark_exhausted("gemini", ttl_seconds=1)
        
        # Should be exhausted now
        assert await QuotaTracker.is_exhausted("gemini") is True
        assert await QuotaTracker.is_exhausted("groq") is False
        
        # Wait for TTL to expire
        await asyncio.sleep(1.1)
        
        # Should be unflagged
        assert await QuotaTracker.is_exhausted("gemini") is False


@pytest.mark.asyncio
async def test_quota_tracker_in_memory_fallback():
    """Test that QuotaTracker falls back to in-memory tracking if Redis is unavailable."""
    # We simulate a Redis connection error by making get_redis_client raise an exception
    class MockRedisErrorContext:
        async def __aenter__(self):
            raise Exception("Redis connection refused")
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # Clear internal in-memory state before test
    QuotaTracker._memory_cache.clear()

    with patch("src.core.quota.get_redis_client", return_value=MockRedisErrorContext()):
        assert await QuotaTracker.is_exhausted("openai") is False
        
        # This should fallback to memory and not raise an error
        await QuotaTracker.mark_exhausted("openai", ttl_seconds=1)
        
        assert await QuotaTracker.is_exhausted("openai") is True
        
        await asyncio.sleep(1.1)
        
        assert await QuotaTracker.is_exhausted("openai") is False


@pytest.mark.asyncio
async def test_quota_manager_redis_success():
    """Test that QuotaManager successfully adds and retrieves quota usage using Redis."""
    from src.core.quota import QuotaManager
    fake_redis = fakeredis.FakeAsyncRedis()
    
    class MockRedisContext:
        async def __aenter__(self):
            from src.core.redis import RedisClient
            return RedisClient(fake_redis)
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("src.core.quota.get_redis_client", return_value=MockRedisContext()):
        await QuotaManager.reset_usage()
        
        # Initial usage should be 0
        usages = await QuotaManager.get_usage()
        for idx in range(1, 5):
            assert usages[idx] == 0
            
        # Add usage
        await QuotaManager.add_usage(1, 500)
        await QuotaManager.add_usage(2, 300)
        await QuotaManager.add_usage(1, 200)
        
        usages = await QuotaManager.get_usage()
        assert usages[1] == 700
        assert usages[2] == 300
        assert usages[3] == 0
        
        # Reset usage
        await QuotaManager.reset_usage()
        usages = await QuotaManager.get_usage()
        assert usages[1] == 0
        assert usages[2] == 0


@pytest.mark.asyncio
async def test_quota_manager_in_memory_fallback():
    """Test that QuotaManager falls back to in-memory tracking if Redis is unavailable."""
    from src.core.quota import QuotaManager
    
    class MockRedisErrorContext:
        async def __aenter__(self):
            raise Exception("Redis connection refused")
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("src.core.quota.get_redis_client", return_value=MockRedisErrorContext()):
        await QuotaManager.reset_usage()
        
        # Initial usage should be 0
        usages = await QuotaManager.get_usage()
        for idx in range(1, 5):
            assert usages[idx] == 0
            
        # Add usage
        await QuotaManager.add_usage(3, 1000)
        await QuotaManager.add_usage(3, 500)
        await QuotaManager.add_usage(4, 250)
        
        usages = await QuotaManager.get_usage()
        assert usages[3] == 1500
        assert usages[4] == 250
        assert usages[1] == 0
