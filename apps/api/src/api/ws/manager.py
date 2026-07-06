import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        # Maps episode_id to a list of active WebSockets
        self.active_connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, episode_id: str) -> None:
        await websocket.accept()
        self.active_connections[episode_id].append(websocket)
        logger.debug(
            "Client connected to episode %s. Total clients: %d",
            episode_id,
            len(self.active_connections[episode_id]),
        )

    def disconnect(self, websocket: WebSocket, episode_id: str) -> None:
        if websocket in self.active_connections[episode_id]:
            self.active_connections[episode_id].remove(websocket)
            logger.debug(
                "Client disconnected from episode %s. Remaining clients: %d",
                episode_id,
                len(self.active_connections[episode_id]),
            )


manager = ConnectionManager()
