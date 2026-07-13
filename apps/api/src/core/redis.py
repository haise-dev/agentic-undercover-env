import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError

from src.core.config import settings

logger = logging.getLogger(__name__)

RETRY_DELAYS: tuple[float, ...] = (0.1, 0.2, 0.4)  # seconds, 3 total attempts

# Global module-level connection pool cache for the default database url
_POOL: aioredis.ConnectionPool | None = None
_POOL_LOCK = asyncio.Lock()


class RedisClient:
    """
    Thin async wrapper around a redis.asyncio.Redis instance.
    Provides typed publish/subscribe helpers and a health check.

    Do not instantiate directly — use get_redis_client() context manager.
    """

    def __init__(self, raw: aioredis.Redis) -> None:
        self.raw: aioredis.Redis = raw

    async def ping(self) -> bool:
        """Returns True if Redis responds to PING, False otherwise. Never raises."""
        try:
            return await self.raw.ping()
        except Exception as exc:
            logger.warning("Redis ping failed: %s", exc)
            return False

    async def publish(self, channel: str, message: dict[str, Any]) -> int:
        """
        Serializes `message` as JSON and publishes to `channel`.
        Returns the number of subscribers that received the message.
        Raises: ValueError if `message` is not JSON-serializable.
        Raises: RedisConnectionError on connection failure.
        """
        try:
            payload = json.dumps(message)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Message must be JSON-serializable: {exc}") from exc

        try:
            count = await self.raw.publish(channel, payload)
            logger.debug("Published to %s: %s", channel, message)
            return count
        except (RedisConnectionError, OSError) as exc:
            logger.error("Failed to publish to channel %s: %s", channel, exc)
            raise RedisConnectionError(f"Redis publish error: {exc}") from exc

    async def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        """
        Async generator. Subscribes to `channel` and yields decoded dicts.
        Uses ignore_subscribe_messages=True to skip control messages.
        Stops when the generator is closed (GeneratorExit).
        """
        pubsub = self.raw.pubsub()
        async with pubsub:
            await pubsub.subscribe(channel)
            try:
                async for msg in pubsub.listen():
                    if msg["type"] != "message":
                        continue
                    raw_data = msg["data"]
                    try:
                        data = json.loads(
                            raw_data.decode("utf-8")
                            if isinstance(raw_data, bytes)
                            else raw_data
                        )
                    except (TypeError, ValueError, json.JSONDecodeError) as exc:
                        logger.error(
                            "Failed to decode JSON from channel %s: %s", channel, exc
                        )
                        raise json.JSONDecodeError(
                            msg=f"Failed to decode message JSON: {exc}",
                            doc=str(raw_data),
                            pos=0,
                        ) from exc

                    logger.debug("Received from %s: %s", channel, data)
                    yield data
            except asyncio.CancelledError:
                logger.debug("Subscription to channel %s cancelled", channel)
                raise

    async def get(self, key: str) -> str | None:
        """Returns the string value for `key`, or None if not found."""
        try:
            val = await self.raw.get(key)
            if val is None:
                return None
            return val.decode("utf-8") if isinstance(val, bytes) else str(val)
        except (RedisConnectionError, OSError) as exc:
            logger.error("Redis get failed for key %s: %s", key, exc)
            raise RedisConnectionError(f"Redis get error: {exc}") from exc

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        """Sets `key` to `value`. `ex` is TTL in seconds (optional)."""
        try:
            await self.raw.set(key, value, ex=ex)
        except (RedisConnectionError, OSError) as exc:
            logger.error("Redis set failed for key %s: %s", key, exc)
            raise RedisConnectionError(f"Redis set error: {exc}") from exc

    async def incrby(self, key: str, amount: int = 1) -> int:
        """Increments the number stored at key by amount."""
        try:
            return await self.raw.incrby(key, amount)
        except (RedisConnectionError, OSError) as exc:
            logger.error("Redis incrby failed for key %s: %s", key, exc)
            raise RedisConnectionError(f"Redis incrby error: {exc}") from exc

    async def delete(self, *keys: str) -> int:
        """Deletes one or more keys. Returns count of deleted keys."""
        if not keys:
            return 0
        try:
            return await self.raw.delete(*keys)
        except (RedisConnectionError, OSError) as exc:
            logger.error("Redis delete failed for keys %s: %s", keys, exc)
            raise RedisConnectionError(f"Redis delete error: {exc}") from exc

    async def rpush(self, key: str, *values: str) -> int:
        """Pushes values to the end of a list. Returns length of list."""
        if not values:
            return 0
        try:
            return await self.raw.rpush(key, *values)
        except (RedisConnectionError, OSError) as exc:
            logger.error("Redis rpush failed for key %s: %s", key, exc)
            raise RedisConnectionError(f"Redis rpush error: {exc}") from exc

    async def lrange(self, key: str, start: int = 0, end: int = -1) -> list[str]:
        """Returns a range of elements from the list stored at key."""
        try:
            vals = await self.raw.lrange(key, start, end)
            return [v.decode("utf-8") if isinstance(v, bytes) else str(v) for v in vals]
        except (RedisConnectionError, OSError) as exc:
            logger.error("Redis lrange failed for key %s: %s", key, exc)
            raise RedisConnectionError(f"Redis lrange error: {exc}") from exc

    async def expire(self, key: str, time: int) -> bool:
        """Sets a timeout on key."""
        try:
            return await self.raw.expire(key, time)
        except (RedisConnectionError, OSError) as exc:
            logger.error("Redis expire failed for key %s: %s", key, exc)
            raise RedisConnectionError(f"Redis expire error: {exc}") from exc


def create_redis_pool(url: str, max_connections: int = 20) -> aioredis.ConnectionPool:
    """
    Creates a Redis connection pool from a URL.
    URL format: redis://host:port/db  or  redis://:password@host:port/db
    Raises ValueError if the URL scheme is not 'redis' or 'rediss'.
    """
    if not (url.startswith("redis://") or url.startswith("rediss://")):
        raise ValueError(
            f"Invalid Redis URL scheme in: {url}. Must start with redis:// or rediss://"
        )
    return aioredis.ConnectionPool.from_url(url, max_connections=max_connections)


async def check_redis_connection(
    client: aioredis.Redis,
    retries: tuple[float, ...] = RETRY_DELAYS,
) -> None:
    """
    Pings Redis with exponential backoff.
    Raises RedisConnectionError if all retries are exhausted.
    Logs each failed attempt at DEBUG level, logs success at INFO level.
    """
    attempts = len(retries) + 1
    for i in range(attempts):
        try:
            await client.ping()
            return
        except (RedisConnectionError, OSError) as exc:
            if i < len(retries):
                delay = retries[i]
                logger.debug(
                    "Redis connection attempt %d failed: %s. Retrying in %ss...",
                    i + 1,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error("Failed to connect to Redis after %d attempts.", attempts)
                raise RedisConnectionError(
                    f"Failed to connect to Redis after {attempts} attempts."
                ) from exc


@asynccontextmanager
async def get_redis_client(
    url: str | None = None,
    pool: aioredis.ConnectionPool | None = None,
    retries: tuple[float, ...] = RETRY_DELAYS,
) -> AsyncIterator[RedisClient]:
    """
    Async context manager yielding a connected RedisClient.
    On entry: verifies connection with exponential backoff ping
    (via check_redis_connection).
    On exit: closes the client connection.

    Priority: if `pool` is provided, use it. Otherwise, create Redis from `url`.
    If neither is provided, uses settings.REDIS_URL.

    Raises: RedisConnectionError after RETRY_DELAYS exhausted.
    """
    if pool is not None:
        target_pool = pool
    else:
        target_url = url or settings.REDIS_URL
        global _POOL
        if target_url == settings.REDIS_URL:
            if _POOL is None:
                async with _POOL_LOCK:
                    if _POOL is None:
                        _POOL = create_redis_pool(target_url)
            target_pool = _POOL
        else:
            target_pool = create_redis_pool(target_url)

    raw_client = aioredis.Redis(connection_pool=target_pool)
    try:
        await check_redis_connection(raw_client, retries=retries)
        yield RedisClient(raw_client)
    finally:
        await raw_client.aclose()
