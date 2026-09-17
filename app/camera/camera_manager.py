"""Camera manager facade pointing to authoritative orion_ai camera subsystem."""

from orion_ai.camera.camera_manager import (
    CameraManager,
    authoritative_camera_manager as camera_manager,
)
from orion_ai.camera.camera_sources import (
    CameraStatus,
    FrameBuffer,
    FrameSource,
    LiveCameraSource,
    ReplayVideoSource,
)

__all__ = [
    "CameraManager",
    "CameraStatus",
    "FrameBuffer",
    "FrameSource",
    "LiveCameraSource",
    "ReplayVideoSource",
    "camera_manager",
]
