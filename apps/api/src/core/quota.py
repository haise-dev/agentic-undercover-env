import logging
import time

from src.core.redis import get_redis_client

logger = logging.getLogger(__name__)


class QuotaTracker:
    """
    Tracks LLM provider rate limit status (exhausted or not).
    Primarily uses Redis for synchronization, with a fallback to local memory
    if Redis is unavailable.
    """

    _memory_cache: dict[str, float] = {}

    @classmethod
    async def mark_exhausted(cls, provider: str, ttl_seconds: int = 300) -> None:
        """
        Flags a provider as exhausted for the specified duration (default 5 mins).
        """
        provider = provider.lower()
        redis_key = f"quota:exhausted:{provider}"
        try:
            async with get_redis_client() as redis:
                await redis.set(redis_key, "1", ex=ttl_seconds)
                logger.info(f"Marked provider '{provider}' as exhausted in Redis for {ttl_seconds}s")
                return
        except Exception as exc:
            logger.warning(
                f"Failed to connect to Redis to mark provider quota: {exc}. Falling back to in-memory."
            )

        # Fallback to local memory
        expiry = time.time() + ttl_seconds
        cls._memory_cache[provider] = expiry
        logger.info(f"Marked provider '{provider}' as exhausted in-memory for {ttl_seconds}s")

    @classmethod
    async def is_exhausted(cls, provider: str) -> bool:
        """
        Checks if a provider is currently flagged as exhausted.
        """
        provider = provider.lower()
        redis_key = f"quota:exhausted:{provider}"
        try:
            async with get_redis_client() as redis:
                val = await redis.get(redis_key)
                if val is not None:
                    return True
        except Exception as exc:
            logger.warning(
                f"Failed to check Redis for provider quota: {exc}. Falling back to in-memory."
            )

        # Fallback / Check local memory
        expiry = cls._memory_cache.get(provider)
        if expiry is not None:
            if time.time() < expiry:
                return True
            else:
                # Cleanup expired entry
                del cls._memory_cache[provider]

        return False


class QuotaManager:
    """
    Tracks and monitors API token usage per API key index.
    Primarily uses Redis for synchronization, with a fallback to local memory
    if Redis is unavailable.
    """

    _memory_usage: dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0}

    @classmethod
    async def add_usage(cls, api_key_index: int, total_tokens: int) -> None:
        """
        Adds token usage to the specified API key index.
        """
        redis_key = f"quota:usage:index:{api_key_index}"
        try:
            async with get_redis_client() as redis:
                await redis.incrby(redis_key, total_tokens)
                return
        except Exception as exc:
            logger.warning(
                f"Failed to connect to Redis to add quota usage: {exc}. Falling back to in-memory."
            )

        # Fallback to local memory
        cls._memory_usage[api_key_index] = cls._memory_usage.get(api_key_index, 0) + total_tokens

    @classmethod
    async def get_usage(cls) -> dict[int, int]:
        """
        Retrieves current token usage for all 4 API key indices.
        """
        usages = {}
        try:
            async with get_redis_client() as redis:
                for idx in range(1, 5):
                    val = await redis.get(f"quota:usage:index:{idx}")
                    usages[idx] = int(val) if val is not None else 0
                return usages
        except Exception as exc:
            logger.warning(
                f"Failed to connect to Redis to get quota usage: {exc}. Falling back to in-memory."
            )

        # Fallback to local memory
        return dict(cls._memory_usage)

    @classmethod
    async def reset_usage(cls) -> None:
        """
        Resets token usage for all indices. Useful for tests.
        """
        try:
            async with get_redis_client() as redis:
                for idx in range(1, 5):
                    await redis.delete(f"quota:usage:index:{idx}")
        except Exception:
            pass
        cls._memory_usage = {1: 0, 2: 0, 3: 0, 4: 0}
