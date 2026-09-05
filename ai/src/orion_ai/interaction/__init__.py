"""Interaction subsystem package."""

from orion_ai.interaction.configs import InteractionConfig
from orion_ai.interaction.interfaces import InteractionDetectorInterface
from orion_ai.interaction.registry import InteractionRegistry
from orion_ai.interaction.schemas import (
    InteractionResult,
    InteractionTriplet,
    SpatialRelation,
)

__all__ = [
    "InteractionConfig",
    "InteractionDetectorInterface",
    "InteractionRegistry",
    "InteractionResult",
    "InteractionTriplet",
    "SpatialRelation",
]
