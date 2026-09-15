"""Detection subsystem package."""

from orion_ai.detection.configs import DetectorConfig
from orion_ai.detection.interfaces import DetectorInterface
from orion_ai.detection.object_detector import (
    DEFAULT_PROTOCOL_CLASSES,
    ObjectDetector,
    tracked_objects_to_observations,
)
from orion_ai.detection.registry import DetectorRegistry
from orion_ai.detection.schemas import BoundingBox2D, DetectionResult, DetectionTarget
from orion_ai.detection.yolo_detector import YOLOEdgeDetector

__all__ = [
    "DEFAULT_PROTOCOL_CLASSES",
    "BoundingBox2D",
    "DetectionResult",
    "DetectionTarget",
    "DetectorConfig",
    "DetectorInterface",
    "DetectorRegistry",
    "ObjectDetector",
    "YOLOEdgeDetector",
    "tracked_objects_to_observations",
]

