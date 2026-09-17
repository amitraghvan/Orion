"""Structured AI observation contract uniting detections, poses, tracks, and telemetry metrics."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from orion_ai.activity.schemas import ActivityPrediction, ActivityRecognitionResult
from orion_ai.detection.schemas import DetectionTarget
from orion_ai.hand.schemas import HandObservation
from orion_ai.interaction.multimodal_schemas import (
    InteractionObservation,
    MultimodalActivityEvidence,
)
from orion_ai.interaction.object_schemas import ObjectObservation
from orion_ai.pose.schemas import HumanPose
from orion_ai.tracking.schemas import TrackedObject


class PipelineMetrics(BaseModel):
    """End-to-end latency and frame-rate performance telemetry."""

    camera_latency_ms: float = 0.0
    detection_latency_ms: float = 0.0
    object_latency_ms: float = 0.0
    pose_latency_ms: float = 0.0
    hand_latency_ms: float = 0.0
    tracking_latency_ms: float = 0.0
    har_latency_ms: float = 0.0
    interaction_latency_ms: float = 0.0
    fusion_latency_ms: float = 0.0
    pipeline_latency_ms: float = 0.0
    fps: float = 0.0
    dropped_frames_total: int = 0
    compute_backend: str = "CPU"
    memory_usage_mb: float = 0.0
    cpu_percent: float = 0.0


class StructuredObservation(BaseModel):
    """Unified multi-modal perception state snapshot for a single optical frame."""

    station_id: str = "BAS-NODE-01"
    frame_index: int
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_id: str
    width: int
    height: int
    detections: list[DetectionTarget] = Field(default_factory=list)
    poses: list[HumanPose] = Field(default_factory=list)
    tracks: list[TrackedObject] = Field(default_factory=list)
    hand_observations: list[HandObservation] = Field(default_factory=list)
    object_observations: list[ObjectObservation] = Field(default_factory=list)
    interaction_observations: list[InteractionObservation] = Field(default_factory=list)
    activities: list[ActivityRecognitionResult] = Field(default_factory=list)
    top_activity: ActivityPrediction | None = None
    multimodal_evidence: MultimodalActivityEvidence | None = None
    metrics: PipelineMetrics = Field(default_factory=PipelineMetrics)
    pipeline_status: str = "NOMINAL"
    system_health: dict[str, str] = Field(default_factory=dict)
    image_jpeg: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Canonical alias properties
    @property
    def timestamp(self) -> datetime:
        return self.timestamp_utc

    @property
    def frame_id(self) -> int:
        return self.frame_index

    @property
    def hands(self) -> list[HandObservation]:
        return self.hand_observations

    @property
    def objects(self) -> list[ObjectObservation]:
        return self.object_observations

    @property
    def interactions(self) -> list[InteractionObservation]:
        return self.interaction_observations

    @property
    def hand_object_interactions(self) -> list[InteractionObservation]:
        return self.interaction_observations

    @property
    def person_detections(self) -> list[DetectionTarget]:
        return [d for d in self.detections if d.class_id == 0 or d.class_name.lower() == "person"]

    @property
    def object_detections(self) -> list[DetectionTarget]:
        return [d for d in self.detections if d.class_id != 0 and d.class_name.lower() != "person"]

    @property
    def har_result(self) -> ActivityRecognitionResult | None:
        return self.activities[0] if self.activities else None

    @property
    def evidence(self) -> MultimodalActivityEvidence | None:
        return self.multimodal_evidence
