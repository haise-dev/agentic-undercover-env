import asyncio
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.api.ws.manager import manager


@pytest.fixture
def client():
    return TestClient(app)


def test_websocket_connect_and_receive(client):
    episode_id = str(uuid.uuid4())

    mock_redis = AsyncMock()

    # Mock historical events
    history_event = json.dumps({"event_type": "HISTORY_EVENT", "payload": {}})
    mock_redis.lrange = AsyncMock(return_value=[history_event])

    # Mock real-time pub/sub events
    async def mock_subscribe(channel):
        yield {"event_type": "NEW_EVENT", "payload": {}}
        # Keep generator alive so websocket doesn't close immediately
        await asyncio.sleep(0.5)

    mock_redis.subscribe = mock_subscribe

    with patch("src.api.ws.game_stream.get_redis_client") as mock_get_redis:
        mock_get_redis.return_value.__aenter__.return_value = mock_redis

        with client.websocket_connect(f"/ws/episodes/{episode_id}/stream") as websocket:
            # 1. Expect history event
            data1 = websocket.receive_json()
            assert data1["event_type"] == "HISTORY_EVENT"

            # 2. Expect real-time event
            data2 = websocket.receive_json()
            assert data2["event_type"] == "NEW_EVENT"

            # 3. Verify manager tracking
            assert episode_id in manager.active_connections
            assert len(manager.active_connections[episode_id]) == 1

        # 4. Disconnected
        assert episode_id not in manager.active_connections or len(manager.active_connections[episode_id]) == 0


def test_websocket_malformed_history(client):
    episode_id = str(uuid.uuid4())

    mock_redis = AsyncMock()
    # Mock malformed historical events (should be skipped)
    mock_redis.lrange = AsyncMock(return_value=["invalid json", json.dumps({"event_type": "VALID"})])

    async def mock_subscribe(channel):
        yield {"event_type": "NEW_EVENT"}
        await asyncio.sleep(0.5)

    mock_redis.subscribe = mock_subscribe

    with patch("src.api.ws.game_stream.get_redis_client") as mock_get_redis:
        mock_get_redis.return_value.__aenter__.return_value = mock_redis

        with client.websocket_connect(f"/ws/episodes/{episode_id}/stream") as websocket:
            # Expect only the valid history event (malformed skipped)
            data1 = websocket.receive_json()
            assert data1["event_type"] == "VALID"
            
            data2 = websocket.receive_json()
            assert data2["event_type"] == "NEW_EVENT"
