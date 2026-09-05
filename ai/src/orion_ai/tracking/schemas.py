"""Object tracking schemas."""

from enum import StrEnum

from pydantic import BaseModel, Field

from orion_ai.detection.schemas import BoundingBox2D


class TrackState(StrEnum):
    """Tracklet lifecycle state."""

    NEW = "NEW"
    TRACKED = "TRACKED"
    LOST = "LOST"
    REMOVED = "REMOVED"


class TrackedObject(BaseModel):
    """Temporal state of a tracked bounding box."""

    track_id: int
    class_id: int
    class_name: str
    box: BoundingBox2D
    velocity_px_per_sec: tuple[float, float] = (0.0, 0.0)
    confidence: float = Field(ge=0.0, le=1.0)
    state: TrackState
    age_frames: int = 1


class TrackingResult(BaseModel):
    """Result of multi-object tracking association for a frame."""

    frame_index: int
    active_tracks: list[TrackedObject]
    lost_tracks: list[int] = Field(default_factory=list)
