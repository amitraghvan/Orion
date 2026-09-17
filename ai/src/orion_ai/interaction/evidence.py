"""Evidence data models for physical grasp and manipulation verification."""

from __future__ import annotations

from pydantic import BaseModel, Field

from orion_ai.interaction.multimodal_schemas import InteractionObservation, InteractionState


class GraspEvidence(BaseModel):
    """Structured physical interaction evidence proving grasp engagement."""

    hand_id: str
    object_id: str
    person_track_id: int
    contact_persistence_frames: int
    overlap_ratio: float
    normalized_distance: float
    confidence: float = Field(ge=0.0, le=1.0)
    is_stable_grasp: bool = False

    @classmethod
    def from_observation(
        cls, obs: InteractionObservation, min_stable_frames: int = 3
    ) -> GraspEvidence:
        """Derive grasp evidence directly from an interaction observation."""
        is_stable = (
            obs.state in (InteractionState.GRASPING, InteractionState.MANIPULATING)
            and obs.contact_persistence_frames >= min_stable_frames
        )
        return cls(
            hand_id=obs.hand_id,
            object_id=obs.object_id,
            person_track_id=obs.person_track_id,
            contact_persistence_frames=obs.contact_persistence_frames,
            overlap_ratio=obs.overlap_ratio,
            normalized_distance=obs.distance_normalized,
            confidence=obs.confidence,
            is_stable_grasp=is_stable,
        )


class ManipulationEvidence(BaseModel):
    """Structured evidence proving sustained dynamic manipulation of payload hardware."""

    hand_id: str
    object_id: str
    person_track_id: int
    grasp_evidence: GraspEvidence
    duration_frames: int
    motion_displacement: float = 0.0
    motion_correlation: float = 0.0
    confidence: float = Field(ge=0.0, le=1.0)
    is_active_manipulation: bool = False

    @classmethod
    def from_observation(
        cls,
        obs: InteractionObservation,
        displacement: float = 0.0,
        correlation: float = 0.0,
        min_manipulation_frames: int = 3,
    ) -> ManipulationEvidence:
        """Derive manipulation evidence from observation and motion metrics."""
        grasp = GraspEvidence.from_observation(obs)
        is_manip = (
            obs.state == InteractionState.MANIPULATING
            and obs.contact_persistence_frames >= min_manipulation_frames
        )
        return cls(
            hand_id=obs.hand_id,
            object_id=obs.object_id,
            person_track_id=obs.person_track_id,
            grasp_evidence=grasp,
            duration_frames=obs.contact_persistence_frames,
            motion_displacement=displacement,
            motion_correlation=correlation,
            confidence=obs.confidence,
            is_active_manipulation=is_manip,
        )
