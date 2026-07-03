import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from redis.exceptions import ConnectionError as RedisConnectionError

from src.main import lifespan


@pytest.mark.asyncio
async def test_lifespan_redis_healthy(capsys):
    """Lifespan pings Redis and logs success when healthy."""
    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()

    mock_get_client = MagicMock()
    mock_get_client.__aenter__.return_value = mock_redis
    mock_get_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.main.get_redis_client", return_value=mock_get_client):
        async with lifespan(MagicMock()):
            pass

    captured = capsys.readouterr()
    assert "Redis connection: OK" in captured.out


@pytest.mark.asyncio
async def test_lifespan_redis_ping_false(capsys):
    """Lifespan logs warning if Redis ping returns False."""
    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(return_value=False)
    mock_redis.aclose = AsyncMock()

    mock_get_client = MagicMock()
    mock_get_client.__aenter__.return_value = mock_redis
    mock_get_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.main.get_redis_client", return_value=mock_get_client):
        async with lifespan(MagicMock()):
            pass

    captured = capsys.readouterr()
    assert "Redis ping returned False" in captured.out


@pytest.mark.asyncio
async def test_lifespan_redis_unreachable(capsys):
    """Lifespan logs CRITICAL error and continues if Redis is unreachable (does not crash)."""
    # RedisConnectionError is raised on context manager entry (e.g. from get_redis_client)
    mock_get_client = MagicMock()
    mock_get_client.__aenter__.side_effect = RedisConnectionError("Refused")

    with patch("src.main.get_redis_client", return_value=mock_get_client):
        # Lifespan should NOT crash (context should enter and yield)
        async with lifespan(MagicMock()):
            pass

    captured = capsys.readouterr()
    assert "FATAL: Cannot connect to Redis" in captured.out
    assert "Pub/Sub features will be unavailable" in captured.out
