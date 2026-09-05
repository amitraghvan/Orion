"""Activity configuration schemas."""

from pydantic import BaseModel, Field


class ActivityConfig(BaseModel):
    """Configuration contract for temporal HAR models."""

    model_id: str
    window_size_frames: int = Field(default=32, ge=8)
    stride_frames: int = Field(default=8, ge=1)
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    allowed_classes: list[str] = Field(default_factory=list)
