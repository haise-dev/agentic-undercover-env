import json
import logging
from datetime import UTC, datetime
from typing import Any

from redis.exceptions import ConnectionError as RedisConnectionError

from src.core.redis import RedisClient

logger = logging.getLogger(__name__)

# Game lifecycle constants
EVT_GAME_START = "GAME_START"
EVT_GAME_OVER = "GAME_OVER"
EVT_GAME_ERROR = "GAME_ERROR"
EVT_ROUND_STARTED = "ROUND_STARTED"

# Agent turns constants
EVT_AGENT_SPOKE = "AGENT_SPOKE"
EVT_AGENT_DELIBERATED = "AGENT_DELIBERATED"

# Voting constants
EVT_POLL_RESULT = "POLL_RESULT"
EVT_VOTE_CAST = "VOTE_CAST"
EVT_ELIMINATION_RESULT = "ELIMINATION_RESULT"

# Reaction sequence constants
EVT_LAST_WORDS = "LAST_WORDS"
EVT_ROLE_REVEAL = "ROLE_REVEAL"
EVT_SURVIVOR_REACTED = "SURVIVOR_REACTED"

# Human player constants
EVT_HUMAN_TURN_REQUEST = "HUMAN_TURN_REQUEST"
EVT_HUMAN_INPUT_RECEIVED = "HUMAN_INPUT_RECEIVED"


class EventEmitter:
    """
    Publishes structured game events to a Redis pub/sub channel.

    All events are published to the channel: `episode:{episode_id}`

    Event envelope format (always):
    {
        "event_type": str,       # e.g. "AGENT_SPOKE", "GAME_OVER"
        "episode_id": str,       # UUID string
        "timestamp": str,        # ISO 8601 UTC
        "payload": dict          # event-specific data
    }
    """

    def __init__(self, redis_client: RedisClient, episode_id: str) -> None:
        """
        Args:
            redis_client: A connected RedisClient instance.
            episode_id: The episode UUID. Used to build the Redis channel name.
        """
        self.redis_client = redis_client
        self.episode_id = episode_id

    @property
    def channel(self) -> str:
        """Returns the Redis channel name: `episode:{episode_id}`"""
        return f"episode:{self.episode_id}"

    async def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        """
        Publishes a game event to the Redis channel.

        Constructs the full envelope and calls redis_client.publish().
        Logs the event at DEBUG level.

        Args:
            event_type: The event type string (e.g. "AGENT_SPOKE").
            payload: Event-specific data dict. Must be JSON-serializable.

        Raises:
            ValueError: if payload is not JSON-serializable.
            RedisConnectionError: if Redis publish fails.
        """
        # Validate JSON serializability first to raise ValueError early
        try:
            json.dumps(payload)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Payload must be JSON-serializable: {exc}") from exc

        envelope = {
            "event_type": event_type,
            "episode_id": self.episode_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": payload,
        }

        try:
            await self.redis_client.publish(self.channel, envelope)
            logger.debug("Emitted %s for episode %s", event_type, self.episode_id)
        except RedisConnectionError as exc:
            logger.error(
                "Failed to emit event %s for episode %s: %s",
                event_type,
                self.episode_id,
                exc,
            )
            raise
