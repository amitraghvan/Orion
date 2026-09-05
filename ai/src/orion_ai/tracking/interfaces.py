"""Tracking interfaces."""

from abc import ABC, abstractmethod

from orion_ai.detection.schemas import DetectionResult
from orion_ai.tracking.schemas import TrackingResult


class TrackerInterface(ABC):
    """Interface for multi-object tracking algorithms (ByteTrack, DeepSORT, BoT-SORT)."""

    @abstractmethod
    def update(self, detections: DetectionResult) -> TrackingResult:
        """Associate detections with active tracks."""
        raise NotImplementedError("NOT IMPLEMENTED: TrackerInterface.update")

    @abstractmethod
    def reset(self) -> None:
        """Purge all active tracklets and reset ID counter."""
        raise NotImplementedError("NOT IMPLEMENTED: TrackerInterface.reset")
