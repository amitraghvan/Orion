"""Camera router for optical feed status and dynamic input source switching."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from orion.core.auth import require_operator, require_viewer
from orion.core.logger import get_logger
from orion.di.container import get_coordinator

logger = get_logger("orion.api.camera")
router = APIRouter(prefix="/camera", tags=["Camera"])


class SwitchCameraSourceRequest(BaseModel):
    """Payload to switch active camera input source."""

    source: str = Field(
        ...,
        description="Source specification: device index integer as string (e.g. '0') or video filepath",
    )


class CameraInfoResponse(BaseModel):
    """Active camera telemetry parameters."""

    camera_id: str
    source: str
    is_active: bool
    is_file: bool
    target_fps: int
    width: int
    height: int
    dropped_frames: int


class CameraStatusResponse(BaseModel):
    """Detailed operational telemetry for optical sensor feed."""

    connected: bool
    state: str
    source: str
    device_index: int | None = None
    width: int
    height: int
    fps: float
    frame_id: int
    last_frame_timestamp: str | None = None
    is_file: bool
    dropped_frames: int
    error: str | None = None


@router.get(
    "/status", response_model=CameraStatusResponse, summary="Get authoritative camera status"
)
async def get_camera_status() -> CameraStatusResponse:
    """Authoritative camera state endpoint used by cockpit to determine connection and FPS."""
    from orion_ai.camera.camera_manager import authoritative_camera_manager

    coordinator = None
    try:
        coordinator = get_coordinator()
    except Exception:
        coordinator = None

    cam = getattr(coordinator, "camera", None) or authoritative_camera_manager
    cam_source = str(getattr(cam, "source", "0"))
    dev_idx = int(cam_source) if cam_source.isdigit() else None

    # Check if either coordinator or camera manager is actively capturing
    is_connected = getattr(cam, "is_connected", False) or getattr(cam, "is_active", False)
    if not is_connected:
        return CameraStatusResponse(
            connected=False,
            state="DISCONNECTED",
            source=cam_source,
            device_index=dev_idx,
            width=getattr(cam, "target_width", 0),
            height=getattr(cam, "target_height", 0),
            fps=0.0,
            frame_id=getattr(cam, "frame_id", 0),
            last_frame_timestamp=None,
            is_file=getattr(cam, "is_file", False),
            dropped_frames=getattr(cam, "dropped_frames", 0),
            error=getattr(cam, "last_error", None),
        )

    last_ts = getattr(cam, "last_frame_timestamp", None)
    ts_str = last_ts.isoformat() if last_ts else None
    fps_val = round(getattr(cam, "actual_fps", 0.0), 1)
    if (
        fps_val == 0.0
        and coordinator
        and coordinator.latest_observation
        and coordinator.latest_observation.metrics
    ):
        fps_val = round(coordinator.latest_observation.metrics.fps, 1)

    is_streaming = (
        coordinator and coordinator.is_running and getattr(coordinator, "frames_processed", 0) > 0
    ) or is_connected
    state_str = getattr(cam, "status", None)
    state_val = getattr(state_str, "value", None) or ("STREAMING" if is_streaming else "CONNECTED")

    return CameraStatusResponse(
        connected=True,
        state=state_val,
        source="live_camera" if dev_idx is not None else cam_source,
        device_index=dev_idx,
        width=getattr(cam, "target_width", 1280),
        height=getattr(cam, "target_height", 720),
        fps=fps_val,
        frame_id=getattr(
            cam, "frame_id", getattr(coordinator, "last_frame_index", 0) if coordinator else 0
        ),
        last_frame_timestamp=ts_str,
        is_file=getattr(cam, "is_file", False),
        dropped_frames=getattr(cam, "dropped_frames", 0),
        error=getattr(cam, "last_error", None),
    )


@router.get("/info", response_model=CameraInfoResponse, summary="Get active camera status")
async def get_camera_info(
    _user: Any = Depends(require_viewer),
) -> CameraInfoResponse:
    """Retrieve operational metrics and parameters for the optical camera feed."""
    try:
        coordinator = get_coordinator()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Perception pipeline coordinator is not running",
        ) from exc

    cam = getattr(coordinator, "camera", None)
    if cam is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Camera driver not attached to coordinator",
        )

    return CameraInfoResponse(
        camera_id=getattr(cam, "camera_id", "cam_optical"),
        source=str(getattr(cam, "source", "0")),
        is_active=getattr(cam, "is_active", False),
        is_file=getattr(cam, "_is_file", False),
        target_fps=getattr(cam, "target_fps", 30),
        width=getattr(cam, "target_width", 640),
        height=getattr(cam, "target_height", 480),
        dropped_frames=getattr(cam, "dropped_frames", 0),
    )


@router.post("/start", summary="Start camera acquisition and inference loop")
async def start_camera(
    _user: Any = Depends(require_operator),
) -> dict[str, Any]:
    """Explicitly open camera and commence optical acquisition."""
    try:
        coordinator = get_coordinator()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Coordinator unavailable: {exc}",
        ) from exc

    try:
        if not coordinator.is_running:
            await coordinator.start()
        return {
            "status": "STARTED",
            "connected": getattr(coordinator.camera, "is_active", False),
            "source": str(getattr(coordinator.camera, "source", "0")),
            "frame_id": getattr(coordinator, "last_frame_index", 0),
        }
    except Exception as exc:
        logger.error("Failed to start camera", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Camera start failed: {exc}",
        ) from exc


@router.post("/stop", summary="Stop camera acquisition and release hardware")
async def stop_camera(
    _user: Any = Depends(require_operator),
) -> dict[str, Any]:
    """Explicitly halt optical capture and release video hardware handle."""
    try:
        coordinator = get_coordinator()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Coordinator unavailable: {exc}",
        ) from exc

    try:
        if coordinator.is_running:
            await coordinator.stop()
        return {
            "status": "STOPPED",
            "connected": False,
        }
    except Exception as exc:
        logger.error("Failed to stop camera", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Camera stop failed: {exc}",
        ) from exc


@router.post("/source", summary="Switch optical camera input source")
async def switch_camera_source(
    request: SwitchCameraSourceRequest,
    _user: Any = Depends(require_operator),
) -> dict[str, Any]:
    """Dynamically switch between live camera device and mission replay video."""
    try:
        coordinator = get_coordinator()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Perception pipeline coordinator is not running",
        ) from exc

    src: str | int = request.source
    if str(src).isdigit():
        src = int(src)

    try:
        await coordinator.switch_camera_source(src)
        return {
            "status": "SWITCHED",
            "source": str(src),
            "camera_id": getattr(coordinator.camera, "camera_id", "cam_optical"),
            "connected": getattr(coordinator.camera, "is_active", False),
        }
    except Exception as exc:
        logger.error("Failed to switch camera source", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to switch optical source: {exc}",
        ) from exc


@router.api_route("/frame", methods=["GET", "HEAD"], summary="Get latest optical frame JPEG")
async def get_optical_frame() -> Response:
    """Retrieve single latest optical frame as binary JPEG image without crashing."""
    from orion_ai.camera.camera_manager import authoritative_camera_manager

    jpeg_bytes: bytes | None = None
    try:
        coordinator = get_coordinator()
        jpeg_bytes = coordinator.latest_jpeg_bytes
    except Exception:
        jpeg_bytes = None

    if not jpeg_bytes:
        jpeg_bytes = authoritative_camera_manager.get_latest_jpeg()

    if not jpeg_bytes:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"status": "disconnected", "error": "Camera frame unavailable"},
        )

    return Response(
        content=jpeg_bytes,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Content-Length": str(len(jpeg_bytes)),
        },
    )


@router.get("/stream", summary="Stream optical video feed via MJPEG")
async def stream_optical_feed() -> StreamingResponse:
    """Stream live optical video via standard multipart/x-mixed-replace MJPEG."""
    import asyncio

    from orion_ai.camera.camera_manager import authoritative_camera_manager

    async def _frame_generator() -> AsyncGenerator[bytes, None]:
        last_frame_sent = -1
        try:
            while True:
                try:
                    coordinator = None
                    try:
                        coordinator = get_coordinator()
                    except Exception:
                        coordinator = None

                    current_idx = getattr(
                        coordinator, "last_frame_index", authoritative_camera_manager.frame_id
                    )
                    if current_idx != last_frame_sent:
                        jpeg = (
                            getattr(coordinator, "latest_jpeg_bytes", None)
                            or authoritative_camera_manager.get_latest_jpeg()
                        )
                        if jpeg:
                            last_frame_sent = current_idx
                            yield (
                                b"--frame\r\n"
                                b"Content-Type: image/jpeg\r\n"
                                b"Content-Length: "
                                + str(len(jpeg)).encode()
                                + b"\r\n\r\n"
                                + jpeg
                                + b"\r\n"
                            )
                except asyncio.CancelledError:
                    break
                except Exception:
                    pass
                await asyncio.sleep(0.015)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        _frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/replays", summary="List available experiment replay videos")
async def list_replays() -> list[dict[str, Any]]:
    """List all available BAS experiment replay recordings for demo and evaluation."""
    import json
    from pathlib import Path

    audit_file = Path("datasets/bas_experiment/reports/raw_data_audit.json")
    if audit_file.is_file():
        try:
            with audit_file.open() as f:
                data = json.load(f)
            return [
                {
                    "video_id": r["video_id"],
                    "filename": r["original_filename"],
                    "path": r["absolute_path"],
                    "is_valid": r["is_valid"],
                    "invalid_type": r["invalid_type"],
                    "subject_id": r["subject_id"],
                    "experiment_id": r["experiment_id"],
                    "variant": r["variant"],
                    "description": r["description"],
                    "duration_seconds": r["duration_seconds"],
                }
                for r in data
            ]
        except Exception:
            pass

    return [
        {
            "video_id": "DEMO_E01_A_VALID",
            "filename": "AP01.mp4",
            "path": "/Users/amitkumar/Downloads/BAS_REAL_DATA/VALID/SP04/AP01.mp4",
            "is_valid": True,
            "invalid_type": None,
            "subject_id": "SP04",
            "experiment_id": "E01",
            "variant": "A",
            "description": "E01 Detecting Colour (Variant A: Yellow then Red)",
            "duration_seconds": 13.1,
        },
        {
            "video_id": "DEMO_WRONG_OBJECT_INVALID",
            "filename": "video_20260912_174946.mp4",
            "path": "/Users/amitkumar/Downloads/BAS_REAL_DATA/INVALID/Invalid data bas/Wrong Object/video_20260912_174946.mp4",
            "is_valid": False,
            "invalid_type": "WRONG_OBJECT",
            "subject_id": "SUB_INVALID",
            "experiment_id": "E01",
            "variant": "A",
            "description": "Protocol Violation: Wrong Object manipulated",
            "duration_seconds": 18.9,
        },
        {
            "video_id": "DEMO_WRONG_ORDER_INVALID",
            "filename": "video_20260912_175307.mp4",
            "path": "/Users/amitkumar/Downloads/BAS_REAL_DATA/INVALID/Invalid data bas/Wrong Order/video_20260912_175307.mp4",
            "is_valid": False,
            "invalid_type": "WRONG_ORDER",
            "subject_id": "SUB_INVALID",
            "experiment_id": "E01",
            "variant": "A",
            "description": "Protocol Violation: Wrong Order of steps",
            "duration_seconds": 17.0,
        },
        {
            "video_id": "DEMO_INTERRUPTION_INVALID",
            "filename": "video_20260912_183146.mp4",
            "path": "/Users/amitkumar/Downloads/BAS_REAL_DATA/INVALID/Invalid data bas/Interruption/video_20260912_183146.mp4",
            "is_valid": False,
            "invalid_type": "INTERRUPTION",
            "subject_id": "SUB_INVALID",
            "experiment_id": "E01",
            "variant": "A",
            "description": "Protocol Violation: Interruption during execution",
            "duration_seconds": 13.4,
        },
    ]
