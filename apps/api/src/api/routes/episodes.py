import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.services.runner_service import RunnerService
from src.core.db import get_session
from src.core.redis import get_redis_client
from src.db.repository import ActionLogRepository, EpisodeRepository
from src.models import ActionLog, EpisodeConfig, EpisodeExport

router = APIRouter()


class EpisodeStatusResponse(BaseModel):
    episode_id: str
    status: str


class EpisodeCreateResponse(BaseModel):
    episode_id: str
    status: str


@router.post(
    "",
    response_model=EpisodeCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new episode",
)
async def create_episode(config: EpisodeConfig) -> EpisodeCreateResponse:
    """
    Accepts an EpisodeConfig and caches it in Redis.
    The episode_id must be provided or one will be generated (by EpisodeConfig).
    The episode is not persisted to PostgreSQL until it completes running.
    """
    # Auto-assign api_key_index (1 to 4) to agents to isolate API keys
    updated_agents = []
    for i, agent in enumerate(config.agents):
        updated_agent = agent.model_copy(update={"api_key_index": i + 1})
        updated_agents.append(updated_agent)
    config = config.model_copy(update={"agents": updated_agents})

    episode_id = config.episode_id

    try:
        async with get_redis_client() as redis:
            key = f"pending_episode:{episode_id}"
            # Cache config for 1 hour (3600 seconds)
            await redis.set(key, config.model_dump_json(), ex=3600)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cache episode config: {exc}",
        )

    return EpisodeCreateResponse(episode_id=episode_id, status="created")


@router.post(
    "/{episode_id}/start",
    response_model=EpisodeStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start an episode in the background",
)
async def start_episode(episode_id: str) -> EpisodeStatusResponse:
    if RunnerService.is_running(episode_id):
        raise HTTPException(status_code=400, detail="Episode is already running")

    try:
        async with get_redis_client() as redis:
            config_str = await redis.get(f"pending_episode:{episode_id}")
            if not config_str:
                raise HTTPException(
                    status_code=404, detail="Pending episode config not found"
                )
            config = EpisodeConfig.model_validate_json(config_str)

        RunnerService.start_episode_task(episode_id, config)
        return EpisodeStatusResponse(episode_id=episode_id, status="started")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/{episode_id}/status",
    response_model=EpisodeStatusResponse,
    summary="Get current running status of an episode",
)
async def get_episode_status(
    episode_id: str, session: AsyncSession = Depends(get_session)
) -> EpisodeStatusResponse:
    if RunnerService.is_running(episode_id):
        return EpisodeStatusResponse(episode_id=episode_id, status="running")

    # Check DB
    episode = await EpisodeRepository.get_by_id(session, episode_id)
    if episode:
        return EpisodeStatusResponse(episode_id=episode_id, status="completed")

    return EpisodeStatusResponse(episode_id=episode_id, status="pending_or_not_found")


@router.get(
    "/{episode_id}",
    response_model=EpisodeExport,
    summary="Get full episode details",
)
async def get_episode(
    episode_id: str,
    session: AsyncSession = Depends(get_session),
) -> EpisodeExport:
    """
    Retrieves a fully completed episode by ID from PostgreSQL.
    Returns 404 if the episode doesn't exist or is still running.
    """
    try:
        uuid.UUID(episode_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found"
        )

    episode = await EpisodeRepository.get_by_id(session, episode_id)
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found"
        )

    return episode


@router.get(
    "/{episode_id}/logs",
    response_model=list[ActionLog],
    summary="Get action logs for an episode",
)
async def get_episode_logs(
    episode_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[ActionLog]:
    """
    Retrieves all action logs associated with a completed episode.
    """
    try:
        uuid.UUID(episode_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No logs found for this episode",
        )

    logs = await ActionLogRepository.get_by_episode(session, episode_id)
    if not logs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No logs found for this episode",
        )

    return logs


@router.get(
    "",
    response_model=list[dict[str, Any]],
    summary="List recent episodes",
)
async def list_episodes(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """
    Returns a lightweight, paginated list of recent completed episodes.
    """
    return await EpisodeRepository.list_recent(session, limit=limit, offset=offset)
