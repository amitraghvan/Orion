"""Interaction configuration schemas."""

from pydantic import BaseModel, Field


class InteractionConfig(BaseModel):
    """Configuration contract for HOI detection."""

    proximity_threshold_px: float = Field(default=80.0, ge=1.0)
    interaction_classes: list[str] = Field(
        default_factory=lambda: ["holds", "operates", "opens", "closes", "inserts", "removes"]
    )
    confidence_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
