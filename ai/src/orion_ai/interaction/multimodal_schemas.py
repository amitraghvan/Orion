"""Multimodal activity and interaction schemas for ORION BAS AI Copilot."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from orion_ai.hand.schemas import HandObservation
from orion_ai.interaction.object_schemas import ObjectObservation


class InteractionState(StrEnum):
    """Fine-grained physical interaction state between a hand and an object."""

    NO_INTERACTION = "no_interaction"
    APPROACHING = "approaching"
    NEAR = "near"
    CONTACT = "contact"
    GRASPING = "grasping"
    MANIPULATING = "manipulating"
    RELEASING = "releasing"
    LOST = "lost"
    UNKNOWN = "unknown"


class InteractionObservation(BaseModel):
    """Dynamic relational observation between a specific hand and object."""

    hand_id: str
    object_id: str
    person_track_id: int
    state: InteractionState
    distance_normalized: float
    overlap_ratio: float
    approach_velocity: float = 0.0
    contact_persistence_frames: int = 0
    confidence: float = Field(ge=0.0, le=1.0)


class EvidenceQualityLevel(StrEnum):
    """Discrete qualitative assessment of multimodal evidence completeness."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"


class EvidenceQuality(BaseModel):
    """Fine-grained and composite quality scores across perception modalities."""

    pose_quality: float = Field(ge=0.0, le=1.0)
    actor_identity_quality: float = Field(ge=0.0, le=1.0)
    hand_quality: float = Field(ge=0.0, le=1.0)
    object_quality: float = Field(ge=0.0, le=1.0)
    interaction_quality: float = Field(ge=0.0, le=1.0)
    temporal_stability: float = Field(ge=0.0, le=1.0)
    overall: EvidenceQualityLevel


class EvidenceState(StrEnum):
    """Overall epistemic state of multimodal evidence for the current action."""

    FULL_EVIDENCE = "FULL_EVIDENCE"
    PARTIAL_EVIDENCE = "PARTIAL_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class MultimodalActivityEvidence(BaseModel):
    """Fused multimodal evidence package linking activity recognition to physical interaction context."""

    activity: str
    person_track_id: int
    hands: list[HandObservation] = Field(default_factory=list)
    objects: list[ObjectObservation] = Field(default_factory=list)
    interactions: list[InteractionObservation] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty_status: str = "NOMINAL"
    evidence_quality: EvidenceQuality
    evidence_state: EvidenceState
    window_start: int
    window_end: int
    frame_ids: list[int] = Field(default_factory=list)
    source_id: str = "primary_payload_camera"
    model_versions: dict[str, str] = Field(default_factory=dict)
