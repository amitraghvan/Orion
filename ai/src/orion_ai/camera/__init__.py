"""Camera subsystem package."""

from orion_ai.camera.camera_manager import CameraManager, authoritative_camera_manager
from orion_ai.camera.camera_sources import (
    CameraStatus,
    FrameBuffer,
    FrameSource,
    LiveCameraSource,
    ReplayVideoSource,
)
from orion_ai.camera.configs import CameraConfig
from orion_ai.camera.interfaces import CameraDriverInterface, FrameCaptureProtocol
from orion_ai.camera.opencv_driver import OpenCVCameraDriver
from orion_ai.camera.registry import CameraRegistry
from orion_ai.camera.schemas import CameraIntrinsics, FrameContract, Resolution

__all__ = [
    "CameraConfig",
    "CameraDriverInterface",
    "CameraIntrinsics",
    "CameraManager",
    "CameraRegistry",
    "CameraStatus",
    "FrameBuffer",
    "FrameCaptureProtocol",
    "FrameContract",
    "FrameSource",
    "LiveCameraSource",
    "OpenCVCameraDriver",
    "ReplayVideoSource",
    "Resolution",
    "authoritative_camera_manager",
]
