"""Activity recognition subsystem package."""

from orion_ai.activity.configs import ActivityConfig
from orion_ai.activity.interfaces import ActivityClassifierInterface
from orion_ai.activity.registry import ActivityRegistry
from orion_ai.activity.schemas import (
    ActivityPrediction,
    ActivityRecognitionResult,
    ActivityWindow,
)

__all__ = [
    "ActivityClassifierInterface",
    "ActivityConfig",
    "ActivityPrediction",
    "ActivityRecognitionResult",
    "ActivityRegistry",
    "ActivityWindow",
]
