import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.services.runner_service import RunnerService, _run_episode_safe, ACTIVE_TASKS
from src.models import EpisodeConfig

@pytest.fixture
def valid_config():
    return EpisodeConfig(
        episode_id=str(uuid.uuid4()),
        topic="Test",
        secret_word="Secret",
        agents=[
            {"agent_id": "a1", "display_name": "A", "display_color": "red", "agent_type": "ai", "llm_config": {"provider": "groq", "model_name": "m"}},
            {"agent_id": "a2", "display_name": "B", "display_color": "red", "agent_type": "ai", "llm_config": {"provider": "groq", "model_name": "m"}},
            {"agent_id": "a3", "display_name": "C", "display_color": "red", "agent_type": "ai", "llm_config": {"provider": "groq", "model_name": "m"}},
            {"agent_id": "a4", "display_name": "D", "display_color": "red", "agent_type": "ai", "llm_config": {"provider": "groq", "model_name": "m"}},
        ],
        max_rounds=1
    )

@pytest.mark.asyncio
async def test_run_episode_safe_success(valid_config):
    episode_id = valid_config.episode_id
    ACTIVE_TASKS[episode_id] = AsyncMock() # dummy task

    mock_redis = AsyncMock()
    mock_runner_instance = AsyncMock()

    with patch("src.api.services.runner_service.get_redis_client") as mock_redis_ctx, \
         patch("src.api.services.runner_service.get_session") as mock_session_ctx, \
         patch("src.api.services.runner_service.EpisodeRunner", return_value=mock_runner_instance), \
         patch("src.api.services.runner_service.AIAgent"):
         
        mock_redis_ctx.return_value.__aenter__.return_value = mock_redis
        
        # Async generator for session
        async def mock_get_session():
            yield AsyncMock(spec=AsyncSession)
            
        mock_session_ctx.side_effect = mock_get_session
        
        await _run_episode_safe(episode_id, valid_config)
        
        # Verify runner was called
        mock_runner_instance.run.assert_called_once()
        # Verify cleanup
        assert episode_id not in ACTIVE_TASKS


@pytest.mark.asyncio
async def test_run_episode_safe_exception_emits_error(valid_config):
    episode_id = valid_config.episode_id
    ACTIVE_TASKS[episode_id] = AsyncMock()

    mock_redis = AsyncMock()
    mock_runner_instance = AsyncMock()
    mock_runner_instance.run.side_effect = Exception("Simulated engine crash")
    
    mock_emitter_instance = AsyncMock()

    with patch("src.api.services.runner_service.get_redis_client") as mock_redis_ctx, \
         patch("src.api.services.runner_service.get_session") as mock_session_ctx, \
         patch("src.api.services.runner_service.EpisodeRunner", return_value=mock_runner_instance), \
         patch("src.api.services.runner_service.EventEmitter", return_value=mock_emitter_instance), \
         patch("src.api.services.runner_service.AIAgent"):
         
        mock_redis_ctx.return_value.__aenter__.return_value = mock_redis
        
        async def mock_get_session():
            yield AsyncMock(spec=AsyncSession)
            
        mock_session_ctx.side_effect = mock_get_session
        
        await _run_episode_safe(episode_id, valid_config)
        
        # Verify emitter was called with GAME_ERROR
        mock_emitter_instance.emit.assert_called_once()
        args = mock_emitter_instance.emit.call_args[0]
        assert args[0] == "GAME_ERROR"
        assert "Simulated engine crash" in args[1]["error"]
        
        # Verify cleanup
        assert episode_id not in ACTIVE_TASKS


def test_start_episode_task(valid_config):
    episode_id = valid_config.episode_id
    
    with patch("src.api.services.runner_service.asyncio.create_task") as mock_create_task:
        mock_create_task.return_value = "mock_task"
        
        RunnerService.start_episode_task(episode_id, valid_config)
        
        assert ACTIVE_TASKS[episode_id] == "mock_task"
        assert RunnerService.is_running(episode_id) is True
        
        # clean up
        del ACTIVE_TASKS[episode_id]
