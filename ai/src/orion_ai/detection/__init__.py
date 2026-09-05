"""Detection subsystem package."""

from orion_ai.detection.configs import DetectorConfig
from orion_ai.detection.interfaces import DetectorInterface
from orion_ai.detection.registry import DetectorRegistry
from orion_ai.detection.schemas import BoundingBox2D, DetectionResult, DetectionTarget

__all__ = [
    "BoundingBox2D",
    "DetectionResult",
    "DetectionTarget",
    "DetectorConfig",
    "DetectorInterface",
    "DetectorRegistry",
]
