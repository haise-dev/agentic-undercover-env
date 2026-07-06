import uuid
import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.api.services.runner_service import RunnerService

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
async def test_start_episode_success(client, valid_episode_config_dict):
    episode_id = valid_episode_config_dict["episode_id"]

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=json.dumps(valid_episode_config_dict))

    with patch("src.api.routes.episodes.get_redis_client") as mock_get_redis:
        mock_get_redis.return_value.__aenter__.return_value = mock_redis
        
        with patch("src.api.routes.episodes.RunnerService.start_episode_task") as mock_start:
            response = await client.post(f"/api/episodes/{episode_id}/start")
            
            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "started"
            assert data["episode_id"] == episode_id
            
            mock_start.assert_called_once()
            args = mock_start.call_args[0]
            assert args[0] == episode_id
            assert args[1].episode_id == episode_id


@pytest.mark.asyncio
async def test_start_episode_already_running(client):
    episode_id = "test-running-id"
    
    with patch("src.api.routes.episodes.RunnerService.is_running", return_value=True):
        response = await client.post(f"/api/episodes/{episode_id}/start")
        assert response.status_code == 400
        assert response.json()["detail"] == "Episode is already running"


@pytest.mark.asyncio
async def test_start_episode_not_found_in_redis(client):
    episode_id = "test-not-found-id"
    
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    
    with patch("src.api.routes.episodes.get_redis_client") as mock_get_redis:
        mock_get_redis.return_value.__aenter__.return_value = mock_redis
        
        response = await client.post(f"/api/episodes/{episode_id}/start")
        assert response.status_code == 404
        assert response.json()["detail"] == "Pending episode config not found"


@pytest.mark.asyncio
async def test_get_episode_status_running(client):
    episode_id = "test-status-running"
    
    with patch("src.api.routes.episodes.RunnerService.is_running", return_value=True):
        response = await client.get(f"/api/episodes/{episode_id}/status")
        assert response.status_code == 200
        assert response.json()["status"] == "running"


@pytest.mark.asyncio
async def test_get_episode_status_completed(client):
    episode_id = "test-status-completed"
    
    with patch("src.api.routes.episodes.RunnerService.is_running", return_value=False):
        with patch("src.api.routes.episodes.EpisodeRepository.get_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"id": episode_id} # mock db result
            
            response = await client.get(f"/api/episodes/{episode_id}/status")
            assert response.status_code == 200
            assert response.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_get_episode_status_pending(client):
    episode_id = "test-status-pending"
    
    with patch("src.api.routes.episodes.RunnerService.is_running", return_value=False):
        with patch("src.api.routes.episodes.EpisodeRepository.get_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            response = await client.get(f"/api/episodes/{episode_id}/status")
            assert response.status_code == 200
            assert response.json()["status"] == "pending_or_not_found"
