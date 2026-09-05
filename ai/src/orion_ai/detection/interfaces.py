"""Detection model interface."""

from abc import ABC, abstractmethod
from typing import Any

from orion_ai.detection.schemas import DetectionResult


class DetectorInterface(ABC):
    """Abstract contract for real-time edge object/crew detector."""

    @abstractmethod
    async def load(self, model_path: str) -> None:
        """Initialize engine and allocate input/output buffers."""
        raise NotImplementedError("NOT IMPLEMENTED: DetectorInterface.load")

    @abstractmethod
    async def detect(self, frame_buffer: Any, frame_index: int) -> DetectionResult:
        """Execute forward pass and return parsed bounding boxes."""
        raise NotImplementedError("NOT IMPLEMENTED: DetectorInterface.detect")

    @abstractmethod
    async def unload(self) -> None:
        """Deallocate weights and runtime context."""
        raise NotImplementedError("NOT IMPLEMENTED: DetectorInterface.unload")
