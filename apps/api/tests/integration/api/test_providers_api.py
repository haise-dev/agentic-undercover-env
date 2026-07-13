import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch

from src.main import app
from src.core.quota import QuotaTracker


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_get_providers_list(client):
    # Ensure cache is clean
    QuotaTracker._memory_cache.clear()

    # Mock Redis client inside QuotaTracker to make it fallback to in-memory cache
    class MockRedisErrorContext:
        async def __aenter__(self):
            raise Exception("No Redis")
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("src.core.quota.get_redis_client", return_value=MockRedisErrorContext()):
        # 1. Get providers, all should have is_exhausted=False
        response = await client.get("/api/providers")
        assert response.status_code == 200
        providers = response.json()
        
        # Verify structure
        assert isinstance(providers, list)
        assert len(providers) > 0
        
        gemini_provider = next((p for p in providers if p["provider"] == "gemini"), None)
        assert gemini_provider is not None
        assert gemini_provider["is_exhausted"] is False
        assert "gemini-2.0-flash" in gemini_provider["models"]

        # 2. Mark gemini exhausted
        await QuotaTracker.mark_exhausted("gemini", ttl_seconds=5)

        # 3. Get providers again, gemini should be exhausted
        response = await client.get("/api/providers")
        assert response.status_code == 200
        providers = response.json()
        
        gemini_provider = next((p for p in providers if p["provider"] == "gemini"), None)
        assert gemini_provider["is_exhausted"] is True
