"""Activity recognition interfaces."""

from abc import ABC, abstractmethod
from typing import Any

from orion_ai.activity.schemas import ActivityRecognitionResult


class ActivityClassifierInterface(ABC):
    """Abstract contract for video transformer / 3D CNN temporal HAR models."""

    @abstractmethod
    async def load(self, model_path: str) -> None:
        """Initialize spatio-temporal model weights."""
        raise NotImplementedError("NOT IMPLEMENTED: ActivityClassifierInterface.load")

    @abstractmethod
    async def classify_window(self, frame_sequence: list[Any]) -> ActivityRecognitionResult:
        """Process window of T frames and output activity classification."""
        raise NotImplementedError("NOT IMPLEMENTED: ActivityClassifierInterface.classify_window")

    @abstractmethod
    async def unload(self) -> None:
        """Release GPU resources."""
        raise NotImplementedError("NOT IMPLEMENTED: ActivityClassifierInterface.unload")
