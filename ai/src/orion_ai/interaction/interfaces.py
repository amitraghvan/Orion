"""Interaction detector interface."""

from abc import ABC, abstractmethod

from orion_ai.detection.schemas import DetectionResult
from orion_ai.interaction.schemas import InteractionResult
from orion_ai.pose.schemas import PoseEstimationResult


class InteractionDetectorInterface(ABC):
    """Abstract contract for spatial-temporal Human-Object Interaction (HOI) inference."""

    @abstractmethod
    def infer_interactions(
        self, detections: DetectionResult, poses: PoseEstimationResult
    ) -> InteractionResult:
        """Infer contact, proximity, and manipulation actions between humans and tools."""
        raise NotImplementedError(
            "NOT IMPLEMENTED: InteractionDetectorInterface.infer_interactions"
        )
