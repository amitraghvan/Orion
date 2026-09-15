"""Progressive deterministic multimodal evidence fusion for human-object interaction."""

from __future__ import annotations

from orion.core.logger import get_logger
from orion_ai.hand.schemas import HandObservation, HandState
from orion_ai.interaction.conflict_detector import ModalityConflictDetector
from orion_ai.interaction.evidence_quality import EvidenceQualityAssessor
from orion_ai.interaction.multimodal_schemas import (
    EvidenceQualityLevel,
    EvidenceState,
    InteractionObservation,
    InteractionState,
    MultimodalActivityEvidence,
)
from orion_ai.interaction.object_schemas import ObjectObservation
from orion_ai.pose.schemas import HumanPose
from orion_ai.tracking.schemas import TrackedObject

logger = get_logger("orion_ai.interaction.fusion")


class DeterministicMultimodalFusion:
    """Deterministic, progressive fusion engine operating across Levels 0 to 3.

    Enriches skeletal HAR classifications with physical object detections, hand states,
    and spatio-temporal interaction proofs without black-box neural ambiguity.
    """

    def __init__(
        self,
        fusion_level: int = 3,
        quality_assessor: EvidenceQualityAssessor | None = None,
        conflict_detector: ModalityConflictDetector | None = None,
    ) -> None:
        self.fusion_level = fusion_level
        self.quality_assessor = quality_assessor or EvidenceQualityAssessor()
        self.conflict_detector = conflict_detector or ModalityConflictDetector()

    def fuse(
        self,
        predicted_activity: str,
        activity_confidence: float,
        person_track_id: int,
        pose: HumanPose | None,
        track: TrackedObject | None,
        hands: list[HandObservation],
        objects: list[ObjectObservation],
        interactions: list[InteractionObservation],
        window_start: int,
        window_end: int,
        frame_ids: list[int] | None = None,
        source_id: str = "primary_payload_camera",
        model_versions: dict[str, str] | None = None,
    ) -> MultimodalActivityEvidence:
        """Execute deterministic fusion and return contextualized evidence package."""
        if frame_ids is None:
            frame_ids = list(range(window_start, window_end + 1))
        if model_versions is None:
            model_versions = {}

        # 1. Assess quality across all perception modalities
        quality = self.quality_assessor.assess(
            pose=pose,
            track=track,
            hands=hands,
            objects=objects,
            interactions=interactions,
        )

        act_lower = predicted_activity.lower().strip()
        is_obj_activity = act_lower in ModalityConflictDetector.OBJECT_REQUIRING_ACTIVITIES

        # Determine evidence state and adjusted confidence across levels
        evidence_state = EvidenceState.FULL_EVIDENCE
        uncertainty_status = "NOMINAL"
        fused_confidence = activity_confidence

        if self.fusion_level == 0:
            # Level 0: Pure ST-GCN passthrough
            evidence_state = EvidenceState.FULL_EVIDENCE

        elif self.fusion_level == 1:
            # Level 1: ST-GCN + Object Presence
            if is_obj_activity:
                if objects:
                    fused_confidence = min(1.0, activity_confidence * 1.1)
                    evidence_state = EvidenceState.FULL_EVIDENCE
                else:
                    fused_confidence = max(0.1, activity_confidence * 0.6)
                    evidence_state = EvidenceState.PARTIAL_EVIDENCE
                    uncertainty_status = "MISSING_OBJECT"
            else:
                evidence_state = EvidenceState.FULL_EVIDENCE

        elif self.fusion_level == 2:
            # Level 2: ST-GCN + Object + Hand Presence
            observed_hands = [h for h in hands if h.state == HandState.OBSERVED]
            if is_obj_activity:
                if objects and observed_hands:
                    fused_confidence = min(1.0, activity_confidence * 1.15)
                    evidence_state = EvidenceState.FULL_EVIDENCE
                elif not objects and not observed_hands:
                    fused_confidence = max(0.1, activity_confidence * 0.4)
                    evidence_state = EvidenceState.INSUFFICIENT_EVIDENCE
                    uncertainty_status = "MISSING_OBJECT_AND_HAND"
                else:
                    fused_confidence = max(0.1, activity_confidence * 0.7)
                    evidence_state = EvidenceState.PARTIAL_EVIDENCE
                    uncertainty_status = "PARTIAL_MODALITY_EVIDENCE"
            else:
                evidence_state = EvidenceState.FULL_EVIDENCE

        elif self.fusion_level >= 3:
            # Level 3: Full Multimodal Interaction Cross-Verification
            conflict_res = self.conflict_detector.check_conflict(
                predicted_activity=predicted_activity,
                activity_confidence=activity_confidence,
                hands=hands,
                objects=objects,
                interactions=interactions,
            )

            if conflict_res.has_conflict:
                evidence_state = EvidenceState.CONFLICTING_EVIDENCE
                uncertainty_status = f"CONFLICT_{conflict_res.conflict_type}"
                fused_confidence = max(0.05, activity_confidence * 0.5)
            elif quality.overall == EvidenceQualityLevel.INSUFFICIENT:
                evidence_state = EvidenceState.INSUFFICIENT_EVIDENCE
                uncertainty_status = "INSUFFICIENT_DATA"
                fused_confidence = max(0.1, activity_confidence * 0.6)
            elif is_obj_activity:
                # Check interaction match
                has_contact_or_grasp = any(
                    i.state in (InteractionState.CONTACT, InteractionState.GRASPING, InteractionState.MANIPULATING)
                    for i in interactions
                )
                has_approach_or_near = any(
                    i.state in (InteractionState.APPROACHING, InteractionState.NEAR)
                    for i in interactions
                )

                if act_lower in ("grasp_tool", "manipulate_sample", "pick_yellow", "pick_red", "place_yellow", "place_red", "check_box", "overlap_boxes") and has_contact_or_grasp:
                    evidence_state = EvidenceState.FULL_EVIDENCE
                    fused_confidence = min(1.0, activity_confidence * 1.2)
                elif act_lower in ("reach_tool", "move_box") and (has_approach_or_near or has_contact_or_grasp):
                    evidence_state = EvidenceState.FULL_EVIDENCE
                    fused_confidence = min(1.0, activity_confidence * 1.15)
                elif not objects:
                    evidence_state = EvidenceState.PARTIAL_EVIDENCE
                    uncertainty_status = "OBJECT_NOT_IN_VIEW"
                    fused_confidence = max(0.2, activity_confidence * 0.7)
                else:
                    evidence_state = EvidenceState.PARTIAL_EVIDENCE
                    uncertainty_status = "INCOMPLETE_INTERACTION"
                    fused_confidence = activity_confidence
            else:
                # Procedural or non-object actions (prepare_workstation, inspect_chamber, idle)
                evidence_state = EvidenceState.FULL_EVIDENCE

        return MultimodalActivityEvidence(
            activity=predicted_activity,
            person_track_id=person_track_id,
            hands=hands,
            objects=objects,
            interactions=interactions,
            confidence=max(0.0, min(1.0, float(fused_confidence))),
            uncertainty_status=uncertainty_status,
            evidence_quality=quality,
            evidence_state=evidence_state,
            window_start=window_start,
            window_end=window_end,
            frame_ids=frame_ids,
            source_id=source_id,
            model_versions=model_versions,
        )
