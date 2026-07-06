import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.ws.manager import manager
from src.core.redis import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter()


async def catchup_and_listen(websocket: WebSocket, episode_id: str) -> None:
    """
    Background task for a websocket connection.
    1. Fetches historical events from the Redis list.
    2. Subscribes to the Redis pub/sub channel for new events.
    """
    try:
        async with get_redis_client() as redis:
            # 1. Catch up missed events
            list_key = f"episode_events:{episode_id}"
            history = await redis.lrange(list_key, 0, -1)
            for raw_evt in history:
                try:
                    evt = json.loads(raw_evt)
                    await websocket.send_json(evt)
                except Exception:
                    logger.warning("Failed to parse historical event from %s", list_key)
                    continue

            # 2. Listen to real-time events via Pub/Sub
            channel = f"episode:{episode_id}"
            async for message in redis.subscribe(channel):
                await websocket.send_json(message)
    except asyncio.CancelledError:
        logger.debug("Catchup and listen task cancelled for episode %s", episode_id)
        raise
    except Exception as exc:
        logger.error("Error in websocket listen task: %s", exc)


@router.websocket("/episodes/{episode_id}/stream")
async def game_stream(websocket: WebSocket, episode_id: str) -> None:
    """
    WebSocket endpoint for observing a game episode.
    """
    await manager.connect(websocket, episode_id)
    listen_task = asyncio.create_task(catchup_and_listen(websocket, episode_id))
    try:
        while True:
            # Block until a message is received or the client disconnects
            # We don't process incoming messages from viewers.
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        logger.debug("Client disconnected normally from episode %s", episode_id)
    except Exception as exc:
        logger.error("WebSocket connection error on episode %s: %s", episode_id, exc)
    finally:
        manager.disconnect(websocket, episode_id)
        listen_task.cancel()
