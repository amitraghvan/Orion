"""Pose estimator interface."""

from abc import ABC, abstractmethod
from typing import Any

from orion_ai.detection.schemas import DetectionResult
from orion_ai.pose.schemas import PoseEstimationResult


class PoseEstimatorInterface(ABC):
    """Abstract contract for human skeleton pose estimation (RTMPose, ViTPose)."""

    @abstractmethod
    async def load(self, model_path: str) -> None:
        """Initialize pose estimation model weights."""
        raise NotImplementedError("NOT IMPLEMENTED: PoseEstimatorInterface.load")

    @abstractmethod
    async def estimate(
        self, frame_buffer: Any, detections: DetectionResult | None = None
    ) -> PoseEstimationResult:
        """Extract 2D/3D human keypoints."""
        raise NotImplementedError("NOT IMPLEMENTED: PoseEstimatorInterface.estimate")

    @abstractmethod
    async def unload(self) -> None:
        """Release pose estimation runtime resources."""
        raise NotImplementedError("NOT IMPLEMENTED: PoseEstimatorInterface.unload")
