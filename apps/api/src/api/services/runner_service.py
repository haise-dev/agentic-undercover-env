import asyncio
import logging

from src.agents.ai_agent import AIAgent
from src.core.db import get_session
from src.core.redis import get_redis_client
from src.engine.event_emitter import EVT_GAME_ERROR, EventEmitter
from src.engine.runner import EpisodeRunner
from src.models import AgentRoleAssignment, EpisodeConfig, Role

logger = logging.getLogger(__name__)

# Registry of active tasks to prevent duplicate runs and garbage collection
ACTIVE_TASKS: dict[str, asyncio.Task] = {}


async def _run_episode_safe(episode_id: str, config: EpisodeConfig) -> None:
    """
    Safely executes an episode runner in the background.
    Manages its own DB session.
    """
    try:
        async with get_redis_client() as redis_client:
            # Create agents with dummy role assignments (they get updated by runner after init)
            agents = {}
            for agent_config in config.agents:
                dummy_role = AgentRoleAssignment(
                    agent_id=agent_config.agent_id,
                    role=Role.VILLAGER,
                    secret_word="dummy",
                    topic="dummy",
                )
                agents[agent_config.agent_id] = AIAgent(agent_config, dummy_role)

            runner = EpisodeRunner(agents=agents, redis_client=redis_client)

            # Create an independent DB session for the background task
            # get_session yields an AsyncSession
            async for db_session in get_session():
                await runner.run(config, db_session)
                break  # only need one session

    except asyncio.CancelledError:
        logger.warning("Episode %s was cancelled", episode_id)
        raise
    except Exception as exc:
        logger.error("Episode %s failed with error: %s", episode_id, exc, exc_info=True)
        # Attempt to emit GAME_ERROR if redis is still reachable
        try:
            async with get_redis_client() as redis_client:
                emitter = EventEmitter(redis_client, episode_id)
                await emitter.emit(EVT_GAME_ERROR, {"error": str(exc)})
        except Exception as emit_exc:
            logger.error("Failed to emit GAME_ERROR for %s: %s", episode_id, emit_exc)
    finally:
        # Cleanup registry
        ACTIVE_TASKS.pop(episode_id, None)
        logger.info("Episode %s task finished and removed from registry", episode_id)


class RunnerService:
    @staticmethod
    def is_running(episode_id: str) -> bool:
        return episode_id in ACTIVE_TASKS

    @staticmethod
    def start_episode_task(episode_id: str, config: EpisodeConfig) -> None:
        """
        Launches the episode runner as a background asyncio.Task.
        """
        task = asyncio.create_task(_run_episode_safe(episode_id, config))
        ACTIVE_TASKS[episode_id] = task
