"""Object and astronaut detection schemas."""

from pydantic import BaseModel, Field


class BoundingBox2D(BaseModel):
    """Normalized or absolute bounding box [x_min, y_min, x_max, y_max]."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def height(self) -> float:
        return self.y_max - self.y_min


class DetectionTarget(BaseModel):
    """Single detected entity in a frame."""

    class_id: int
    class_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    box: BoundingBox2D
    track_id: int | None = None


class DetectionResult(BaseModel):
    """Output batch of detections for a single frame."""

    frame_index: int
    timestamp_sensor_ns: int
    detections: list[DetectionTarget]
    inference_latency_ms: float
