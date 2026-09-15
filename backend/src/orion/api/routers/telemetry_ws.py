import asyncio
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from orion.core.auth import authenticate_ws, require_viewer
from orion.core.logger import get_logger
from orion.core.metrics import WEBSOCKET_BROADCASTS_TOTAL, WEBSOCKET_CLIENTS
from orion.di.container import get_settings
from orion.health.interfaces import SubsystemReport, SubsystemStatus
from orion_ai.runtime.observation import StructuredObservation

logger = get_logger("orion.api.telemetry_ws")
router = APIRouter(tags=["Telemetry WebSocket"])

TRANSIENT_EVENT_TYPES = {
    "TELEMETRY_FRAME",
    "FrameCaptured",
    "DetectionCompleted",
    "PoseCompleted",
}

CLIENT_QUEUE_MAXSIZE = 16


class TelemetryStreamStatus(BaseModel):
    """Queryable telemetry streaming health and client metrics."""

    status: str = "NOMINAL"
    active_clients: int = Field(ge=0)
    streaming_enabled: bool = True
    messages_dispatched: int = Field(ge=0)
    messages_dropped: int = Field(default=0, ge=0)


class WebSocketConnectionManager:
    """Manages active telemetry WebSocket connections with per-client bounded queues."""

    def __init__(self, queue_maxsize: int = CLIENT_QUEUE_MAXSIZE) -> None:
        self.queue_maxsize = queue_maxsize
        self._client_queues: dict[WebSocket, asyncio.Queue[dict[str, Any]]] = {}
        self._sender_tasks: dict[WebSocket, asyncio.Task[None]] = {}
        self.messages_dispatched: int = 0
        self.messages_dropped: int = 0
        self._total_connections: int = 0
        self._disconnected_clients: int = 0
        self._last_broadcast_utc: datetime | None = None
        self._broadcasts_attempted: int = 0

    @property
    def active_connections(self) -> list[WebSocket]:
        """Return list of active connected client sockets."""
        return list(self._client_queues.keys())

    @property
    def total_connections(self) -> int:
        """Return cumulative connected clients since process launch."""
        return self._total_connections

    @property
    def disconnected_clients(self) -> int:
        """Return cumulative disconnected clients."""
        return self._disconnected_clients

    @property
    def last_broadcast_timestamp(self) -> datetime | None:
        """Return timestamp of most recent broadcast fanout."""
        return self._last_broadcast_utc

    async def connect(self, websocket: WebSocket) -> None:
        """Register a new client connection and spawn its dedicated sender task."""
        await websocket.accept()
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self.queue_maxsize)
        self._client_queues[websocket] = queue
        sender_task = asyncio.create_task(self._client_sender(websocket, queue))
        self._sender_tasks[websocket] = sender_task
        self._total_connections += 1
        WEBSOCKET_CLIENTS.set(len(self._client_queues))
        logger.info("WebSocket client connected", active_clients=len(self._client_queues))

    def disconnect(self, websocket: WebSocket) -> None:
        """Deregister client connection and cancel its sender task."""
        if websocket in self._sender_tasks:
            task = self._sender_tasks.pop(websocket)
            task.cancel()
        if websocket in self._client_queues:
            del self._client_queues[websocket]
            self._disconnected_clients += 1
            WEBSOCKET_CLIENTS.set(len(self._client_queues))
        logger.info("WebSocket client disconnected", active_clients=len(self._client_queues))

    async def _client_sender(
        self, websocket: WebSocket, queue: asyncio.Queue[dict[str, Any]]
    ) -> None:
        """Dedicated per-client background sender loop."""
        try:
            while True:
                payload = await queue.get()
                try:
                    await websocket.send_json(payload)
                    self.messages_dispatched += 1
                except Exception as exc:
                    logger.debug("Failed sending WebSocket message to client", error=str(exc))
                    break
                finally:
                    queue.task_done()
        except asyncio.CancelledError:
            pass
        finally:
            self.disconnect(websocket)

    async def broadcast_json(self, payload: dict[str, Any]) -> None:
        """Fanout JSON payload to all active client queues with drop-oldest for frames."""
        if not self._client_queues:
            return

        self._broadcasts_attempted += 1
        self._last_broadcast_utc = datetime.now(UTC)
        WEBSOCKET_BROADCASTS_TOTAL.inc()

        is_transient = payload.get("type") in TRANSIENT_EVENT_TYPES
        for _ws, queue in list(self._client_queues.items()):
            if queue.full():
                if is_transient:
                    # Drop oldest transient frame to prevent head-of-line blocking
                    try:
                        queue.get_nowait()
                        queue.task_done()
                        self.messages_dropped += 1
                    except asyncio.QueueEmpty:
                        pass
                else:
                    # For critical/durable events, evict oldest transient event if possible
                    try:
                        queue.get_nowait()
                        queue.task_done()
                        self.messages_dropped += 1
                    except asyncio.QueueEmpty:
                        pass

            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                self.messages_dropped += 1
                logger.warning(
                    "Dropped message for saturated client", event_type=payload.get("type")
                )

    async def broadcast_observation(self, observation: StructuredObservation) -> None:
        """Broadcast typed perception observation to all connected clients."""
        payload = {
            "type": "TELEMETRY_FRAME",
            "station_id": observation.station_id,
            "frame_index": observation.frame_index,
            "timestamp_utc": observation.timestamp_utc.isoformat(),
            "source_id": observation.source_id,
            "width": observation.width,
            "height": observation.height,
            "detections": [d.model_dump() for d in observation.detections],
            "poses": [p.model_dump() for p in observation.poses],
            "tracks": [t.model_dump() for t in observation.tracks],
            "activities": [a.model_dump() for a in observation.activities],
            "top_activity": (
                observation.top_activity.activity_name if observation.top_activity else None
            ),
            "hands": [h.model_dump(mode="json") for h in observation.hand_observations],
            "objects": [o.model_dump(mode="json") for o in observation.object_observations],
            "interactions": [i.model_dump(mode="json") for i in observation.interaction_observations],
            "multimodal_evidence": (
                observation.multimodal_evidence.model_dump(mode="json")
                if observation.multimodal_evidence
                else None
            ),
            "metrics": observation.metrics.model_dump(),
            "pipeline_status": observation.pipeline_status,
            "image_jpeg": None,
        }
        await self.broadcast_json(payload)

    def get_health_report(self) -> SubsystemReport:
        """Produce standardized subsystem health diagnostic report."""
        now = datetime.now(UTC)
        status = SubsystemStatus.HEALTHY
        err = None
        if self.messages_dropped > 0 and self.messages_dropped >= self.messages_dispatched:
            status = SubsystemStatus.DEGRADED
            err = f"High message drop rate: {self.messages_dropped} dropped vs {self.messages_dispatched} dispatched"

        return SubsystemReport(
            subsystem_id="websocket",
            status=status,
            timestamp=now,
            last_success=self._last_broadcast_utc,
            latency_ms=0.0,
            metrics={
                "active_clients": len(self._client_queues),
                "total_connections": self._total_connections,
                "disconnected_clients": self._disconnected_clients,
                "broadcasts_attempted": self._broadcasts_attempted,
                "messages_dispatched": self.messages_dispatched,
                "messages_dropped": self.messages_dropped,
            },
            details={
                "queue_maxsize": self.queue_maxsize,
            },
            error_message=err,
        )



manager = WebSocketConnectionManager()


@router.websocket("/ws/telemetry")
async def telemetry_websocket_endpoint(websocket: WebSocket) -> None:
    """Live telemetry stream WebSocket endpoint broadcasting perception observations."""
    secret_key = (
        websocket.app.state.settings.api.secret_key
        if hasattr(websocket.app.state, "settings") and websocket.app.state.settings is not None
        else get_settings().api.secret_key
    )
    user = authenticate_ws(websocket, secret_key)
    if user is None:
        logger.warning("Unauthenticated WebSocket connection rejected")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return

    logger.info("WebSocket client authenticated", sub=user.sub, role=user.role)
    await manager.connect(websocket)
    try:
        # Send initial connection handshake
        await websocket.send_json(
            {
                "type": "SYSTEM_STATUS",
                "message": "Connected to ORION real-time optical telemetry feed",
                "phase": "1",
                "status": "NOMINAL",
            }
        )

        # Send initial experiment status if protocol service is active
        try:
            from orion.di.container import get_protocol_service

            service = get_protocol_service()
            await websocket.send_json(
                {
                    "type": "EXPERIMENT_STATUS",
                    **service.get_status_payload(),
                }
            )
        except Exception as exc:
            logger.debug("Initial experiment status unavailable on WS connect", error=str(exc))

        # Keep connection open and listen for client heartbeats/pings
        while True:
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                break
    finally:
        manager.disconnect(websocket)


@router.get("/ws/status", response_model=TelemetryStreamStatus, summary="Telemetry Stream Status")
async def get_stream_status(
    _user: object = Depends(require_viewer),
) -> TelemetryStreamStatus:
    """Return live telemetry broadcaster metrics and connection count."""
    return TelemetryStreamStatus(
        status="NOMINAL",
        active_clients=len(manager.active_connections),
        streaming_enabled=True,
        messages_dispatched=manager.messages_dispatched,
        messages_dropped=manager.messages_dropped,
    )
