"""Detection configuration schemas."""

from pydantic import BaseModel, Field


class DetectorConfig(BaseModel):
    """Configuration contract for object detection models."""

    model_id: str
    confidence_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    max_detections: int = Field(default=100, ge=1)
    target_classes: list[str] = Field(default_factory=list)
    input_shape: tuple[int, int] = (640, 640)
