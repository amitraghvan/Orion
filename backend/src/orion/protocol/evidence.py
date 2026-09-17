"""Protocol Evidence data structures for linking perception outputs to scientific validation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from orion.events.schemas import ActivityRecognized


class ProtocolEvidence(BaseModel):
    """Immutable evidence snapshot linking computer vision/HAR observations to protocol decisions."""

    track_id: int = 0
    frame_index: int = 0
    window_start_frame: int = 0
    window_end_frame: int = 0
    activity_label: str
    mapped_action: str
    confidence: float
    entropy: float = 0.0
    uncertainty_status: str = "NOMINAL"
    probabilities: dict[str, float] = Field(default_factory=dict)
    bbox: list[float] | None = None
    keypoints_summary: dict[str, Any] | None = None
    captured_at_iso: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    # Multimodal interaction enrichment
    hand_observations_summary: list[dict[str, Any]] | None = None
    object_observations_summary: list[dict[str, Any]] | None = None
    interaction_state: str | None = None
    evidence_quality_level: str | None = None
    evidence_state: str | None = None
    multimodal_confidence: float | None = None

    @classmethod
    def from_activity_event(
        cls,
        event: ActivityRecognized,
        mapped_action: str,
        entropy: float | None = None,
    ) -> ProtocolEvidence:
        """Construct ProtocolEvidence from an incoming ActivityRecognized event."""
        metadata = event.evidence_metadata or {}
        probabilities = metadata.get("probabilities", {})
        calc_entropy = entropy if entropy is not None else float(metadata.get("entropy", 0.0))
        bbox = metadata.get("bbox")
        keypoints_summary = metadata.get("keypoints_summary")

        return cls(
            track_id=event.track_id,
            frame_index=event.frame_index,
            window_start_frame=event.window_start_frame,
            window_end_frame=event.window_end_frame,
            activity_label=event.activity_label,
            mapped_action=mapped_action,
            confidence=float(event.confidence),
            entropy=calc_entropy,
            uncertainty_status=event.uncertainty_status,
            probabilities=probabilities,
            bbox=bbox,
            keypoints_summary=keypoints_summary,
            captured_at_iso=event.timestamp.isoformat()
            if hasattr(event, "timestamp") and event.timestamp
            else datetime.now(UTC).isoformat(),
            hand_observations_summary=metadata.get("hands")
            or metadata.get("hand_observations_summary"),
            object_observations_summary=metadata.get("objects")
            or metadata.get("object_observations_summary"),
            interaction_state=metadata.get("interaction_state"),
            evidence_quality_level=metadata.get("evidence_quality_level"),
            evidence_state=metadata.get("evidence_state"),
            multimodal_confidence=float(metadata["multimodal_confidence"])
            if "multimodal_confidence" in metadata
            else None,
        )
