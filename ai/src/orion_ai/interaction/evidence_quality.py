"""Evidence quality assessment evaluating multi-modal perception signals."""

from __future__ import annotations

from orion_ai.hand.schemas import HandObservation, HandState
from orion_ai.interaction.multimodal_schemas import (
    EvidenceQuality,
    EvidenceQualityLevel,
    InteractionObservation,
)
from orion_ai.interaction.object_schemas import ObjectObservation
from orion_ai.pose.schemas import HumanPose
from orion_ai.tracking.schemas import TrackedObject


class EvidenceQualityAssessor:
    """Assesses perceptual completeness across pose, identity, hand, object, and interaction modalities."""

    def __init__(
        self,
        high_thresh: float = 0.75,
        med_thresh: float = 0.50,
        low_thresh: float = 0.25,
    ) -> None:
        self.high_thresh = high_thresh
        self.med_thresh = med_thresh
        self.low_thresh = low_thresh

    def assess(
        self,
        pose: HumanPose | None,
        track: TrackedObject | None,
        hands: list[HandObservation],
        objects: list[ObjectObservation],
        interactions: list[InteractionObservation],
        temporal_stability: float = 0.85,
    ) -> EvidenceQuality:
        """Compute structured quality ratings for each modality and overall composite level."""
        # 1. Pose quality
        pose_q = 0.0
        if pose is not None:
            kpt_scores = [k.score for k in pose.keypoints_2d if k.score > 0.1]
            if kpt_scores:
                pose_q = max(0.0, min(1.0, float(sum(kpt_scores) / len(kpt_scores))))
            else:
                pose_q = pose.overall_confidence

        # 2. Identity / Tracking quality
        actor_q = 0.0
        if track is not None:
            # Older stable tracks get higher identity quality
            actor_q = max(0.0, min(1.0, track.confidence))
        elif pose is not None and pose.person_id:
            actor_q = 0.5

        # 3. Hand quality
        hand_q = 0.0
        if hands:
            scores: list[float] = []
            for h in hands:
                if h.state == HandState.OBSERVED:
                    scores.append(max(0.8, h.confidence))
                elif h.state == HandState.PARTIAL:
                    scores.append(max(0.4, h.confidence))
                elif h.state == HandState.OCCLUDED:
                    scores.append(0.2)
                else:
                    scores.append(0.0)
            hand_q = float(sum(scores) / len(scores))

        # 4. Object quality
        obj_q = 0.0
        if objects:
            obj_scores = [o.confidence for o in objects]
            obj_q = float(sum(obj_scores) / len(obj_scores))

        # 5. Interaction quality
        int_q = 0.0
        if interactions:
            int_scores = [i.confidence for i in interactions]
            int_q = float(sum(int_scores) / len(int_scores))

        # Composite score
        composite = (
            0.25 * pose_q
            + 0.15 * actor_q
            + 0.20 * hand_q
            + 0.20 * obj_q
            + 0.10 * int_q
            + 0.10 * temporal_stability
        )

        overall: EvidenceQualityLevel
        if composite >= self.high_thresh:
            overall = EvidenceQualityLevel.HIGH
        elif composite >= self.med_thresh:
            overall = EvidenceQualityLevel.MEDIUM
        elif composite >= self.low_thresh:
            overall = EvidenceQualityLevel.LOW
        else:
            overall = EvidenceQualityLevel.INSUFFICIENT

        return EvidenceQuality(
            pose_quality=max(0.0, min(1.0, pose_q)),
            actor_identity_quality=max(0.0, min(1.0, actor_q)),
            hand_quality=max(0.0, min(1.0, hand_q)),
            object_quality=max(0.0, min(1.0, obj_q)),
            interaction_quality=max(0.0, min(1.0, int_q)),
            temporal_stability=max(0.0, min(1.0, temporal_stability)),
            overall=overall,
        )
