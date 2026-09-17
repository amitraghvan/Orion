"""Human Activity Recognition (HAR) temporal schemas and versioned contracts."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from orion_ai.detection.schemas import BoundingBox2D


class KeypointState(StrEnum):
    """Reliability state of an individual skeletal keypoint."""

    OBSERVED = "OBSERVED"
    INTERPOLATED = "INTERPOLATED"
    HELD = "HELD"
    INVALID = "INVALID"


class TemporalKeypoint(BaseModel):
    """2D keypoint coordinate with confidence and reliability state."""

    id: int
    name: str
    x: float
    y: float
    score: float = Field(ge=0.0, le=1.0)
    state: KeypointState = KeypointState.OBSERVED


class TemporalSkeletonPose(BaseModel):
    """Single-frame skeletal snapshot of an individual tracked astronaut."""

    frame_index: int
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))
    track_id: int
    bbox: BoundingBox2D
    keypoints_2d: list[TemporalKeypoint]
    overall_confidence: float = Field(ge=0.0, le=1.0)


class ActivityWindow(BaseModel):
    """Temporal frame window metadata for action recognition."""

    window_id: str = ""
    start_frame: int
    end_frame: int
    fps: int = 30
    duration_seconds: float = 1.0
    stride: int = 8
    track_id: int = 0


class ActivityPhase(StrEnum):
    """Semantic progression phase of an ongoing activity."""

    START = "START"
    UPDATE = "UPDATE"
    CHANGE = "CHANGE"
    END = "END"


class UncertaintyStatus(StrEnum):
    """Epistemic evaluation state of the temporal classification engine."""

    NOMINAL = "NOMINAL"
    UNKNOWN = "UNKNOWN"
    UNCERTAIN = "UNCERTAIN"
    WARMING_UP = "WARMING_UP"
    DEGRADED = "DEGRADED"
    INVALID_SEQUENCE = "INVALID_SEQUENCE"


class ActivityPrediction(BaseModel):
    """Class probability distribution and metadata for recognized human actions."""

    activity_name: str
    phase: ActivityPhase = ActivityPhase.UPDATE
    confidence: float = Field(ge=0.0, le=1.0)
    probabilities: dict[str, float] = Field(default_factory=dict)
    uncertainty_status: UncertaintyStatus = UncertaintyStatus.NOMINAL
    is_nominal: bool = True
    model_version: str = "1.0.0"


class ActivityRecognitionResult(BaseModel):
    """Aggregated temporal action recognition result for an individual subject."""

    track_id: int = 0
    window: ActivityWindow
    top_prediction: ActivityPrediction
    candidates: list[ActivityPrediction] = Field(default_factory=list)
    uncertainty_status: UncertaintyStatus = UncertaintyStatus.NOMINAL
    latency_ms: float = 0.0

    @property
    def activity(self) -> str:
        """Name of the recognized top activity."""
        return self.top_prediction.activity_name

    @property
    def confidence(self) -> float:
        """Confidence score of the recognized top activity."""
        return self.top_prediction.confidence


# ------------------------------------------------------------------------------
# Ground-Truth Activity Taxonomy
# ------------------------------------------------------------------------------

TRAINED_ACTIVITY_CLASSES: list[str] = [
    "prepare_workstation",
    "reach_tool",
    "grasp_tool",
    "manipulate_sample",
    "inspect_chamber",
    "idle",
]

CLASS_TO_INDEX: dict[str, int] = {name: idx for idx, name in enumerate(TRAINED_ACTIVITY_CLASSES)}
INDEX_TO_CLASS: dict[int, str] = dict(enumerate(TRAINED_ACTIVITY_CLASSES))

MACRO_ACTIVITIES: set[str] = {"prepare_workstation"}
ATOMIC_ACTIVITIES: set[str] = {
    "reach_tool",
    "grasp_tool",
    "manipulate_sample",
    "inspect_chamber",
    "idle",
}
