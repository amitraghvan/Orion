"""Camera driver and frame capture interfaces."""

from abc import ABC, abstractmethod
from typing import Any

from orion_ai.camera.schemas import CameraIntrinsics, FrameContract


class FrameCaptureProtocol(ABC):
    """Protocol for frame buffer acquisition."""

    @abstractmethod
    async def read_frame(self) -> tuple[FrameContract, Any]:
        """Fetch frame contract and raw numpy/tensor memory buffer."""
        raise NotImplementedError("NOT IMPLEMENTED: FrameCaptureProtocol.read_frame")


class CameraDriverInterface(FrameCaptureProtocol, ABC):
    """Complete sensor lifecycle controller interface."""

    @abstractmethod
    async def initialize(self) -> None:
        """Power up sensor and configure register controls."""
        raise NotImplementedError("NOT IMPLEMENTED: CameraDriverInterface.initialize")

    @abstractmethod
    async def shutdown(self) -> None:
        """Safely disengage sensor stream."""
        raise NotImplementedError("NOT IMPLEMENTED: CameraDriverInterface.shutdown")

    @abstractmethod
    def get_intrinsics(self) -> CameraIntrinsics:
        """Return optical calibration matrices."""
        raise NotImplementedError("NOT IMPLEMENTED: CameraDriverInterface.get_intrinsics")
