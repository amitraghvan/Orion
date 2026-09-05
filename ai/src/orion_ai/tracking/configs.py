"""Tracking configuration schemas."""

from pydantic import BaseModel, Field


class TrackerConfig(BaseModel):
    """Configuration contract for multi-object tracking."""

    tracker_type: str = "bytetrack"
    track_thresh: float = Field(default=0.5, ge=0.0, le=1.0)
    match_thresh: float = Field(default=0.8, ge=0.0, le=1.0)
    max_time_lost_frames: int = Field(default=30, ge=1)
