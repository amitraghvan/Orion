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
    track_id: int = 0
    frame_index: int = 0
    window_start_frame: int
    window_end_frame: int
    activity_label: str
    phase: str = "UPDATE"  # START, UPDATE, CHANGE, END
    confidence: float
    uncertainty_status: str = "NOMINAL"
    is_anomaly: bool = False
    model_version: str = "1.0.0"
    evidence_metadata: dict[str, Any] = Field(default_factory=dict)


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
    status: Literal["HEALTHY", "DEGRADED", "UNHEALTHY", "OFFLINE", "ERROR", "UNKNOWN"]
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


class ProtocolStateChanged(BaseEvent):
    """Emitted when the protocol FSM state changes."""

    event_type: Literal["ProtocolStateChanged"] = "ProtocolStateChanged"
    experiment_id: str
    run_id: str | None = None
    from_state: str
    to_state: str
    step_id: str | None = None
    step_number: int | None = None
    reason: str = ""


class StepTransitioned(BaseEvent):
    """Emitted when an experiment step successfully completes and transitions."""

    event_type: Literal["StepTransitioned"] = "StepTransitioned"
    experiment_id: str
    run_id: str
    from_step_id: str
    to_step_id: str
    from_step_number: int
    to_step_number: int
    duration_seconds: float
    decision_id: str


class ProtocolDeviationDetected(BaseEvent):
    """Emitted when an out-of-sequence, skipped, or timeout deviation occurs."""

    event_type: Literal["ProtocolDeviationDetected"] = "ProtocolDeviationDetected"
    experiment_id: str
    run_id: str
    step_id: str
    step_number: int
    deviation_type: str
    observed_action: str
    expected_actions: list[str]
    confidence: float
    entropy: float
    message: str
    decision_id: str


class NextStepRecommended(BaseEvent):
    """Emitted when procedural guidance updates for the astronaut."""

    event_type: Literal["NextStepRecommended"] = "NextStepRecommended"
    experiment_id: str
    run_id: str
    step_id: str
    step_number: int
    expected_activity: str
    instruction_text: str
    remaining_nominal_seconds: float


class HandInteractionStarted(BaseEvent):
    """Emitted when contact or approach between hand and object begins."""

    event_type: Literal["HandInteractionStarted"] = "HandInteractionStarted"
    hand_id: str
    object_id: str
    person_track_id: int
    initial_state: str
    distance_normalized: float
    overlap_ratio: float


class HandInteractionUpdated(BaseEvent):
    """Emitted when interaction state changes or persists."""

    event_type: Literal["HandInteractionUpdated"] = "HandInteractionUpdated"
    hand_id: str
    object_id: str
    person_track_id: int
    previous_state: str
    current_state: str
    contact_persistence_frames: int
    confidence: float


class HandInteractionEnded(BaseEvent):
    """Emitted when hand releases or disengages from object."""

    event_type: Literal["HandInteractionEnded"] = "HandInteractionEnded"
    hand_id: str
    object_id: str
    person_track_id: int
    final_state: str
    duration_frames: int


class ObjectInteractionRecognized(BaseEvent):
    """Emitted when physical grasp or manipulation of a protocol object is verified."""

    event_type: Literal["ObjectInteractionRecognized"] = "ObjectInteractionRecognized"
    hand_id: str
    object_id: str
    object_class: str
    person_track_id: int
    interaction_type: str
    confidence: float


class MultimodalEvidenceUpdated(BaseEvent):
    """Emitted when fused multimodal evidence is updated for an activity."""

    event_type: Literal["MultimodalEvidenceUpdated"] = "MultimodalEvidenceUpdated"
    activity: str
    person_track_id: int
    evidence_state: str
    evidence_quality_level: str
    confidence: float
    uncertainty_status: str


class EvidenceQualityChanged(BaseEvent):
    """Emitted when sensory quality drops or changes."""

    event_type: Literal["EvidenceQualityChanged"] = "EvidenceQualityChanged"
    previous_level: str
    current_level: str
    pose_quality: float
    hand_quality: float
    object_quality: float
    details: str = ""


class InteractionConflictDetected(BaseEvent):
    """Emitted when optical observation contradicts predicted activity."""

    event_type: Literal["InteractionConflictDetected"] = "InteractionConflictDetected"
    activity: str
    conflict_type: str
    reason: str
    severity: str = "WARNING"


class ObservationCaptured(BaseEvent):
    """Emitted when a consolidated StructuredObservation is generated by the perception coordinator."""

    event_type: Literal["ObservationCaptured"] = "ObservationCaptured"
    observation: Any = Field(description="StructuredObservation instance")


# ==============================================================================
# Canonical Domain Events (Section 11)
# ==============================================================================


class ObjectDetected(BaseEvent):
    """Emitted when specific objects or persons are detected in the frame."""

    event_type: Literal["ObjectDetected"] = "ObjectDetected"
    frame_index: int
    object_count: int
    classes: list[str]
    confidences: list[float] = Field(default_factory=list)
    bboxes: list[list[float]] = Field(default_factory=list)


class PoseDetected(BaseEvent):
    """Emitted when human pose keypoints are detected."""

    event_type: Literal["PoseDetected"] = "PoseDetected"
    frame_index: int
    person_count: int
    keypoints_summary: list[dict[str, Any]] = Field(default_factory=list)


class HandDetected(BaseEvent):
    """Emitted when human hand ROIs are extracted."""

    event_type: Literal["HandDetected"] = "HandDetected"
    frame_index: int
    hand_count: int
    hands: list[dict[str, Any]] = Field(default_factory=list)


class InteractionDetected(BaseEvent):
    """Emitted when hand-object interaction is detected."""

    event_type: Literal["InteractionDetected"] = "InteractionDetected"
    frame_index: int
    interaction_type: str
    hand_id: str
    object_id: str
    confidence: float


class ActionRecognized(BaseEvent):
    """Canonical action recognition event (alias / subtype of ActivityRecognized)."""

    event_type: Literal["ActionRecognized"] = "ActionRecognized"
    action: str
    confidence: float
    timestamp_epoch: float = 0.0
    temporal_window: tuple[int, int] = (0, 0)
    uncertainty_status: str = "NOMINAL"


class StepStarted(BaseEvent):
    """Emitted when an experiment step begins."""

    event_type: Literal["StepStarted"] = "StepStarted"
    experiment_id: str
    run_id: str
    step_id: str
    step_number: int
    step_name: str = ""


class StepCompleted(BaseEvent):
    """Emitted when an experiment step successfully completes."""

    event_type: Literal["StepCompleted"] = "StepCompleted"
    experiment_id: str
    run_id: str
    step_id: str
    step_number: int
    duration_seconds: float = 0.0


class StepViolation(BaseEvent):
    """Emitted when a step violation occurs (e.g. wrong object, out of sequence)."""

    event_type: Literal["StepViolation"] = "StepViolation"
    experiment_id: str
    run_id: str
    step_id: str
    step_number: int
    violation_type: str
    message: str


class ExperimentStarted(BaseEvent):
    """Emitted when an experiment execution run commences."""

    event_type: Literal["ExperimentStarted"] = "ExperimentStarted"
    experiment_id: str
    run_id: str
    protocol_version: str = "1.0.0"


class ExperimentCompleted(BaseEvent):
    """Emitted when an experiment execution run finishes successfully."""

    event_type: Literal["ExperimentCompleted"] = "ExperimentCompleted"
    experiment_id: str
    run_id: str
    total_duration_seconds: float = 0.0
    total_steps: int = 0


class ExperimentFailed(BaseEvent):
    """Emitted when an experiment execution run terminates with failure."""

    event_type: Literal["ExperimentFailed"] = "ExperimentFailed"
    experiment_id: str
    run_id: str
    error_code: str
    reason: str


class VoiceRequested(BaseEvent):
    """Emitted when an audio / voice alert is requested."""

    event_type: Literal["VoiceRequested"] = "VoiceRequested"
    message: str
    priority: str = "NORMAL"
    voice_id: str = "default"
