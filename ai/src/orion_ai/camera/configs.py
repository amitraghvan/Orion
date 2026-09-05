"""Camera configuration models."""

from pydantic import BaseModel, Field


class CameraConfig(BaseModel):
    """Configuration contract for an optical sensor."""

    camera_id: str
    source_uri: str
    width: int = Field(default=1920, ge=320)
    height: int = Field(default=1080, ge=240)
    fps: int = Field(default=30, ge=1, le=240)
    auto_reconnect: bool = True
    reconnect_delay_seconds: float = 2.0
