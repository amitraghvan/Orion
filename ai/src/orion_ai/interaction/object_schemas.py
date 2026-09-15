"""Object perception schemas for ORION BAS AI Copilot."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from orion_ai.detection.schemas import BoundingBox2D


class ObjectObservation(BaseModel):
    """Spatial and semantic observation of a protocol-relevant object."""

    object_id: str
    class_name: str
    bbox: BoundingBox2D
    confidence: float = Field(ge=0.0, le=1.0)
    track_id: int | None = None
    frame_index: int
    timestamp: datetime
    source_id: str
