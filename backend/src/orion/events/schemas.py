"""Typed Pydantic event schemas for ORION BAS AI Copilot internal bus."""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """Base schema for all typed telemetry events."""

    event_id: UUID = Field(default_factory=uuid4, description="Globally unique event identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC event occurrence timestamp",
    )
    station_id: str = Field(default="BAS-NODE-01", description="Emitting station module")
    event_type: str = Field(..., description="Discriminator event name")


class FrameCaptured(BaseEvent):
    """Emitted when a raw sensor frame is successfully pulled into the memory buffer."""

    event_type: Literal["FrameCaptured"] = "FrameCaptured"
    camera_id: str
    frame_index: int
    width: int
    height: int
    pixel_format: str
    timestamp_sensor_ns: int
    latency_ms: float


class DetectionCompleted(BaseEvent):
    """Emitted when object/crew bounding box detection concludes."""

    event_type: Literal["DetectionCompleted"] = "DetectionCompleted"
    frame_index: int
    detection_count: int
    classes_detected: list[str]
    inference_time_ms: float


class PoseCompleted(BaseEvent):
    """Emitted when human 17/133-keypoint 2D/3D estimation completes."""

    event_type: Literal["PoseCompleted"] = "PoseCompleted"
    frame_index: int
    person_count: int
    topology: str
    inference_time_ms: float


class ActivityRecognized(BaseEvent):
    """Emitted when temporal human activity recognition classifies a window."""

    event_type: Literal["ActivityRecognized"] = "ActivityRecognized"
    window_start_frame: int
    window_end_frame: int
    activity_label: str
    confidence: float
    is_anomaly: bool


class ExperimentUpdated(BaseEvent):
    """Emitted when scientific experiment step advances or status mutates."""

    event_type: Literal["ExperimentUpdated"] = "ExperimentUpdated"
    experiment_id: str
    run_id: str
    previous_step_id: str | None
    current_step_id: str
    status: Literal["PENDING", "RUNNING", "PAUSED", "COMPLETED", "FAILED", "ABORTED"]


class AlertRaised(BaseEvent):
    """Emitted when an operational or safety alert is flagged by any subsystem."""

    event_type: Literal["AlertRaised"] = "AlertRaised"
    alert_id: UUID = Field(default_factory=uuid4)
    subsystem: str
    severity: Literal["INFO", "WARNING", "CRITICAL", "EMERGENCY"]
    code: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)


class HealthChanged(BaseEvent):
    """Emitted when a monitored subsystem changes operational status."""

    event_type: Literal["HealthChanged"] = "HealthChanged"
    subsystem: str
    status: Literal["HEALTHY", "DEGRADED", "UNHEALTHY", "OFFLINE"]
    metrics: dict[str, float] = Field(default_factory=dict)
    details: str | None = None


class RecordingStarted(BaseEvent):
    """Emitted when a new video recording segment begins."""

    event_type: Literal["RecordingStarted"] = "RecordingStarted"
    recording_id: str
    experiment_id: str
    file_path: str
    resolution: tuple[int, int]
    fps: int


class RecordingStopped(BaseEvent):
    """Emitted when video recording stops and file is finalized/hashed."""

    event_type: Literal["RecordingStopped"] = "RecordingStopped"
    recording_id: str
    file_path: str
    duration_seconds: float
    total_frames: int
    sha256_checksum: str
