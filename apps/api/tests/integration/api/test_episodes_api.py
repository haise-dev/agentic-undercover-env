import asyncio
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repository import ActionLogRepository, EpisodeRepository
from src.main import app
from src.models import (
    ActionLog,
    EpisodeConfig,
    EpisodeExport,
    GameResult,
    Phase,
)

# Use httpx.AsyncClient for integration tests instead of TestClient
@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


@pytest.fixture
def valid_episode_config_dict():
    return {
        "episode_id": str(uuid.uuid4()),
        "topic": "Technology",
        "secret_word": "Robot",
        "agents": [
            {
                "agent_id": "a1",
                "display_name": "Alice",
                "display_color": "red",
                "agent_type": "ai",
                "llm_config": {"provider": "groq", "model_name": "llama3"}
            },
            {
                "agent_id": "a2",
                "display_name": "Bob",
                "display_color": "blue",
                "agent_type": "ai",
                "llm_config": {"provider": "groq", "model_name": "llama3"}
            },
            {
                "agent_id": "a3",
                "display_name": "Charlie",
                "display_color": "green",
                "agent_type": "ai",
                "llm_config": {"provider": "groq", "model_name": "llama3"}
            },
            {
                "agent_id": "a4",
                "display_name": "Diana",
                "display_color": "yellow",
                "agent_type": "ai",
                "llm_config": {"provider": "groq", "model_name": "llama3"}
            }
        ],
        "max_rounds": 3
    }


@pytest.mark.asyncio
async def test_post_episode_valid(client, valid_episode_config_dict):
    # Mock Redis client
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)

    with patch("src.api.routes.episodes.get_redis_client") as mock_get_redis:
        mock_get_redis.return_value.__aenter__.return_value = mock_redis

        response = await client.post("/api/episodes", json=valid_episode_config_dict)
        assert response.status_code == 201
        data = response.json()
        assert "episode_id" in data
        assert data["status"] == "created"

        # Verify Redis was called to cache the config
        mock_redis.set.assert_called_once()
        args, kwargs = mock_redis.set.call_args
        assert args[0].startswith("pending_episode:")
        # Should have a TTL
        assert kwargs.get("ex") is not None


@pytest.mark.asyncio
async def test_post_episode_invalid_agents(client, valid_episode_config_dict):
    invalid_dict = valid_episode_config_dict.copy()
    invalid_dict["agents"] = invalid_dict["agents"][:3]  # Only 3 agents

    response = await client.post("/api/episodes", json=invalid_dict)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_episode_not_found(client):
    fake_id = str(uuid.uuid4())
    with patch("src.api.routes.episodes.EpisodeRepository.get_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        response = await client.get(f"/api/episodes/{fake_id}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Episode not found"


@pytest.mark.asyncio
async def test_get_episode_logs_not_found(client):
    fake_id = str(uuid.uuid4())
    with patch("src.api.routes.episodes.ActionLogRepository.get_by_episode", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        response = await client.get(f"/api/episodes/{fake_id}/logs")
        assert response.status_code == 404
        assert response.json()["detail"] == "No logs found for this episode"


@pytest.mark.asyncio
async def test_get_episode_invalid_uuid(client):
    response = await client.get("/api/episodes/not-a-uuid")
    assert response.status_code in (422, 404)


@pytest.mark.asyncio
async def test_list_recent_episodes(client):
    with patch("src.api.routes.episodes.EpisodeRepository.list_recent", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [{"id": "123", "status": "done"}]
        response = await client.get("/api/episodes?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["id"] == "123"

