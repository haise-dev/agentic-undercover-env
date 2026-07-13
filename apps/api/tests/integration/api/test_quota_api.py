import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch

from src.main import app
from src.core.quota import QuotaManager


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_get_quota_api(client):
    # Mock Redis client inside QuotaManager to use in-memory fallback cleanly
    class MockRedisErrorContext:
        async def __aenter__(self):
            raise Exception("No Redis")
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("src.core.quota.get_redis_client", return_value=MockRedisErrorContext()):
        # 1. Reset usage
        await QuotaManager.reset_usage()

        # 2. Get initial quota usage via API
        response = await client.get("/api/quota")
        assert response.status_code == 200
        usages = response.json()
        assert len(usages) == 4
        for item in usages:
            assert item["total_tokens"] == 0

        # 3. Simulate adding token usage
        await QuotaManager.add_usage(1, 1000)
        await QuotaManager.add_usage(2, 2500)

        # 4. Fetch quota again and assert updated numbers
        response = await client.get("/api/quota")
        assert response.status_code == 200
        usages = response.json()
        
        # Verify index 1
        item_1 = next(item for item in usages if item["api_key_index"] == 1)
        assert item_1["total_tokens"] == 1000

        # Verify index 2
        item_2 = next(item for item in usages if item["api_key_index"] == 2)
        assert item_2["total_tokens"] == 2500

        # Verify index 3
        item_3 = next(item for item in usages if item["api_key_index"] == 3)
        assert item_3["total_tokens"] == 0
