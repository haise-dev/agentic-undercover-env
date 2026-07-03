import pytest
from unittest.mock import MagicMock

from src.models import EpisodeConfig
from src.engine.runner import EpisodeRunner
from src.engine.event_emitter import EventEmitter


def test_runner_init_validation():
    mock_redis = MagicMock()

    # Valid: 4 agents
    valid_agents = {"a1": 1, "a2": 2, "a3": 3, "a4": 4}
    runner = EpisodeRunner(valid_agents, mock_redis)
    assert runner is not None
    assert runner.emitter is None

    # Invalid: 3 agents
    invalid_3 = {"a1": 1, "a2": 2, "a3": 3}
    with pytest.raises(ValueError) as exc_info:
        EpisodeRunner(invalid_3, mock_redis)
    assert "EpisodeRunner requires exactly 4 agents" in str(exc_info.value)

    # Invalid: 5 agents
    invalid_5 = {"a1": 1, "a2": 2, "a3": 3, "a4": 4, "a5": 5}
    with pytest.raises(ValueError) as exc_info:
        EpisodeRunner(invalid_5, mock_redis)
    assert "EpisodeRunner requires exactly 4 agents" in str(exc_info.value)


@pytest.mark.asyncio
async def test_runner_run_raises_not_implemented(episode_config):
    mock_redis = MagicMock()
    valid_agents = {"a1": 1, "a2": 2, "a3": 3, "a4": 4}
    runner = EpisodeRunner(valid_agents, mock_redis)

    assert runner.emitter is None

    with pytest.raises(NotImplementedError) as exc_info:
        await runner.run(episode_config)

    assert "EpisodeRunner.run() is not yet implemented" in str(exc_info.value)

    # Verify that emitter is set when run starts
    assert runner.emitter is not None
    assert isinstance(runner.emitter, EventEmitter)
    assert runner.emitter.channel == f"episode:{episode_config.episode_id}"
