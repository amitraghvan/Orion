"""Human Activity Recognition (HAR) temporal schemas."""

from pydantic import BaseModel, Field


class ActivityWindow(BaseModel):
    """Temporal frame window metadata for action recognition."""

    start_frame: int
    end_frame: int
    fps: int = 30
    duration_seconds: float


class ActivityPrediction(BaseModel):
    """Class probability distribution for recognized human actions."""

    activity_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    is_nominal: bool = True  # Flagged false if unexpected or anomalous in experiment protocol


class ActivityRecognitionResult(BaseModel):
    """Aggregated temporal action recognition result."""

    window: ActivityWindow
    top_prediction: ActivityPrediction
    candidates: list[ActivityPrediction] = Field(default_factory=list)
    latency_ms: float
