"""Hand perception schemas for ORION BAS AI Copilot."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from orion_ai.detection.schemas import BoundingBox2D
from orion_ai.pose.schemas import Keypoint2D


class HandSide(StrEnum):
    """Anatomical hand side."""

    LEFT = "left"
    RIGHT = "right"
    UNKNOWN = "unknown"


class HandState(StrEnum):
    """Visibility / detection state of the hand."""

    OBSERVED = "observed"
    PARTIAL = "partial"
    OCCLUDED = "occluded"
    MISSING = "missing"
    INVALID = "invalid"


class HandObservation(BaseModel):
    """Per-hand spatial observation derived from skeleton or hand detector."""

    hand_id: str
    side: HandSide
    person_track_id: int
    wrist_keypoint: Keypoint2D | None = None
    region_bbox: BoundingBox2D | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    state: HandState
    frame_index: int
    timestamp: datetime
    source_id: str
