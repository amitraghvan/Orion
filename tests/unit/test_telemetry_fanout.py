"""Unit tests for WebSocketConnectionManager bounded per-client queues and drop-oldest policy."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from orion.api.routers.telemetry_ws import WebSocketConnectionManager


@pytest.mark.asyncio
async def test_websocket_bounded_queue_drop_oldest() -> None:
    """Verify that slow clients drop oldest frame events when queue capacity is reached."""
    # Manager with small queue size for fast test verification
    manager = WebSocketConnectionManager(queue_maxsize=4)

    # Mock client WebSocket that never drains its queue (simulates stalled network)
    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_json = AsyncMock()

    # We manually register the queue without spawning sender task to test queue behavior directly
    queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=4)
    manager._client_queues[mock_ws] = queue

    # Push 6 high-frequency frame events
    for frame_idx in range(1, 7):
        await manager.broadcast_json(
            {
                "type": "TELEMETRY_FRAME",
                "frame_index": frame_idx,
            }
        )

    # Queue size should not exceed capacity (4)
    assert queue.qsize() == 4
    # 2 oldest frames should have been dropped
    assert manager.messages_dropped == 2

    # The remaining frames in queue should be the newest frames: 3, 4, 5, 6
    remaining_indices = []
    while not queue.empty():
        item = queue.get_nowait()
        remaining_indices.append(item["frame_index"])

    assert remaining_indices == [3, 4, 5, 6]


@pytest.mark.asyncio
async def test_websocket_client_connect_disconnect() -> None:
    """Verify connect and disconnect properly manage queues and sender tasks."""
    manager = WebSocketConnectionManager(queue_maxsize=8)

    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_json = AsyncMock()

    await manager.connect(mock_ws)
    assert mock_ws in manager.active_connections
    assert len(manager.active_connections) == 1
    assert mock_ws in manager._client_queues
    assert mock_ws in manager._sender_tasks

    manager.disconnect(mock_ws)
    assert mock_ws not in manager.active_connections
    assert len(manager.active_connections) == 0
    assert mock_ws not in manager._client_queues
    assert mock_ws not in manager._sender_tasks
