"""Conflict detection between skeletal activity classifications and physical interaction evidence."""

from __future__ import annotations

from dataclasses import dataclass

from orion_ai.hand.schemas import HandObservation, HandState
from orion_ai.interaction.multimodal_schemas import InteractionObservation, InteractionState
from orion_ai.interaction.object_schemas import ObjectObservation


@dataclass
class ConflictCheckResult:
    """Outcome of modality cross-verification check."""

    has_conflict: bool
    conflict_type: str | None = None
    reason: str | None = None
    severity: str = "INFO"  # INFO, WARNING, CRITICAL


class ModalityConflictDetector:
    """Audits temporal HAR activity predictions against physical scene objects and hand states."""

    # Activities requiring object interaction
    OBJECT_REQUIRING_ACTIVITIES: set[str] = {
        "reach_tool",
        "grasp_tool",
        "manipulate_sample",
        "pick_yellow",
        "place_yellow",
        "pick_red",
        "place_red",
        "move_box",
        "check_box",
        "overlap_boxes",
    }

    def check_conflict(
        self,
        predicted_activity: str,
        activity_confidence: float,
        hands: list[HandObservation],
        objects: list[ObjectObservation],
        interactions: list[InteractionObservation],
    ) -> ConflictCheckResult:
        """Evaluate if physical evidence contradicts the predicted activity."""
        act_lower = predicted_activity.lower().strip()

        # Check 1: Tool/sample interaction claimed but zero objects in scene
        if act_lower in self.OBJECT_REQUIRING_ACTIVITIES and activity_confidence >= 0.5:
            if not objects:
                return ConflictCheckResult(
                    has_conflict=True,
                    conflict_type="MISSING_TARGET_OBJECT",
                    reason=f"Activity '{predicted_activity}' predicted with {activity_confidence:.2f} confidence, but zero protocol objects are detected in the visual frame.",
                    severity="WARNING",
                )

            # Check 2: Grasp/Manipulate claimed, but all hands are MISSING
            visible_hands = [h for h in hands if h.state in (HandState.OBSERVED, HandState.PARTIAL)]
            if not visible_hands:
                return ConflictCheckResult(
                    has_conflict=True,
                    conflict_type="MISSING_HAND_EVIDENCE",
                    reason=f"Activity '{predicted_activity}' predicted, but no hand keypoints or regions are observable.",
                    severity="WARNING",
                )

            # Check 3: Active grasp claimed, but interaction state is far away (NO_INTERACTION with distance > 0.5)
            if act_lower in ("grasp_tool", "manipulate_sample") and activity_confidence >= 0.7:
                contact_or_near = [
                    i for i in interactions
                    if i.state in (InteractionState.CONTACT, InteractionState.GRASPING, InteractionState.MANIPULATING, InteractionState.NEAR)
                ]
                if interactions and not contact_or_near:
                    min_dist = min(i.distance_normalized for i in interactions)
                    if min_dist > 0.4:
                        return ConflictCheckResult(
                            has_conflict=True,
                            conflict_type="SPATIAL_DISCONNECT",
                            reason=f"Activity '{predicted_activity}' claimed, but closest hand-object distance is {min_dist:.2f} (exceeds proximity boundary).",
                            severity="WARNING",
                        )

        # Check 4: Idle claimed, but sustained manipulation of tools is occurring
        if act_lower == "idle" and activity_confidence >= 0.6:
            active_manipulations = [
                i for i in interactions if i.state in (InteractionState.GRASPING, InteractionState.MANIPULATING)
            ]
            if active_manipulations:
                return ConflictCheckResult(
                    has_conflict=True,
                    conflict_type="UNREPORTED_MANIPULATION",
                    reason="Temporal HAR classifies astronaut as 'idle', but active hand-object grasping/manipulation is detected.",
                    severity="WARNING",
                )

        return ConflictCheckResult(has_conflict=False)
