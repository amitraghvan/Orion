"""WebSocket telemetry feed interface."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.exceptions import HTTPException

from orion.core.logger import get_logger

logger = get_logger("orion.api.telemetry_ws")
router = APIRouter(tags=["Telemetry WebSocket"])


@router.websocket("/ws/telemetry")
async def telemetry_websocket_endpoint(websocket: WebSocket) -> None:
    """Telemetry stream WebSocket contract.

    In Phase 0, connection is accepted and immediately notified of non-implementation.
    """
    await websocket.accept()
    try:
        await websocket.send_json(
            {
                "type": "SYSTEM_STATUS",
                "message": "NOT IMPLEMENTED: Real-time telemetry streaming runtime is not implemented in Phase 0.",
                "phase": "0",
            }
        )
        await websocket.close(code=status.WS_1000_NORMAL_CLOSURE, reason="NOT IMPLEMENTED")
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


@router.get("/ws/status", summary="Telemetry Stream Status")
async def get_stream_status() -> dict[str, str]:
    """Endpoint contract for queryable telemetry streaming status."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="NOT IMPLEMENTED: Telemetry stream status is not implemented in Phase 0.",
    )
