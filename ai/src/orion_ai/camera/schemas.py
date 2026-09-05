"""Camera schemas for raw sensor frame contracts and optical metadata."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class Resolution(BaseModel):
    """Sensor optical dimensions."""

    width: int = Field(ge=1)
    height: int = Field(ge=1)


class CameraIntrinsics(BaseModel):
    """Pinhole camera model intrinsic matrix and distortion polynomial."""

    fx: float
    fy: float
    cx: float
    cy: float
    distortion_coeffs: list[float] = Field(default_factory=list)


class FrameContract(BaseModel):
    """Metadata contract accompanying an in-memory frame buffer."""

    camera_id: str
    frame_index: int
    resolution: Resolution
    channels: int = 3
    pixel_format: Literal["RGB8", "BGR8", "GRAY8", "YUV420"] = "RGB8"
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))
    timestamp_sensor_ns: int
