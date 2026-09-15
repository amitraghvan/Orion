"""Temporal interaction state machine with temporal hysteresis and microgravity stability."""

from __future__ import annotations

from dataclasses import dataclass, field

from orion.core.logger import get_logger
from orion_ai.interaction.geometry import GeometricInteractionFeatures
from orion_ai.interaction.hand_object_associator import HandObjectCandidate
from orion_ai.interaction.multimodal_schemas import InteractionObservation, InteractionState

logger = get_logger("orion_ai.interaction.state_machine")


@dataclass
class PairTracklet:
    """Historical interaction state between a specific hand and object."""

    hand_id: str
    object_id: str
    person_track_id: int
    current_state: InteractionState = InteractionState.NO_INTERACTION
    frames_in_state: int = 0
    contact_persistence_frames: int = 0
    consecutive_near_frames: int = 0
    consecutive_motion_frames: int = 0
    last_seen_frame: int = 0
    last_features: GeometricInteractionFeatures | None = None
    state_history: list[InteractionState] = field(default_factory=list)


class InteractionStateMachine:
    """Multi-stage temporal state tracker enforcing hysteresis for HOI states.

    Prevents transient optical flickers from falsely triggering physical grasps or manipulations.
    """

    def __init__(
        self,
        min_approach_frames: int = 2,
        min_grasp_frames: int = 3,
        min_manipulate_frames: int = 3,
        min_release_frames: int = 2,
        max_lost_frames: int = 5,
        prune_after_frames: int = 30,
    ) -> None:
        self.min_approach_frames = min_approach_frames
        self.min_grasp_frames = min_grasp_frames
        self.min_manipulate_frames = min_manipulate_frames
        self.min_release_frames = min_release_frames
        self.max_lost_frames = max_lost_frames
        self.prune_after_frames = prune_after_frames

        self._tracklets: dict[tuple[str, str], PairTracklet] = {}
        self._prev_distances: dict[tuple[str, str], float] = {}

    def get_previous_distance(self, hand_id: str, object_id: str) -> float | None:
        return self._prev_distances.get((hand_id, object_id))

    def update(
        self,
        candidates: list[HandObjectCandidate],
        frame_index: int,
    ) -> list[InteractionObservation]:
        """Process candidate associations, update temporal state machines, and return observations."""
        seen_pairs: set[tuple[str, str]] = set()
        observations: list[InteractionObservation] = []

        for cand in candidates:
            pair_key = (cand.hand.hand_id, cand.obj.object_id)
            seen_pairs.add(pair_key)

            tracklet = self._tracklets.get(pair_key)
            if tracklet is None:
                tracklet = PairTracklet(
                    hand_id=cand.hand.hand_id,
                    object_id=cand.obj.object_id,
                    person_track_id=cand.hand.person_track_id,
                    last_seen_frame=frame_index,
                )
                self._tracklets[pair_key] = tracklet

            # Record distance for velocity calculation in subsequent frames
            self._prev_distances[pair_key] = cand.features.normalized_distance

            # Update hysteresis metrics
            if cand.features.is_in_contact:
                tracklet.contact_persistence_frames += 1
            else:
                tracklet.contact_persistence_frames = 0

            if cand.features.is_near:
                tracklet.consecutive_near_frames += 1
            else:
                tracklet.consecutive_near_frames = 0

            # State transition logic with hysteresis
            old_state = tracklet.current_state
            new_state = self._evaluate_transition(tracklet, cand, frame_index)

            if new_state == old_state:
                tracklet.frames_in_state += 1
            else:
                tracklet.current_state = new_state
                tracklet.frames_in_state = 1
                logger.debug(
                    "HOI state transition",
                    pair=pair_key,
                    from_state=old_state.value,
                    to_state=new_state.value,
                    frame=frame_index,
                )

            tracklet.last_seen_frame = frame_index
            tracklet.last_features = cand.features
            tracklet.state_history.append(new_state)
            if len(tracklet.state_history) > 60:
                tracklet.state_history.pop(0)

            # Confidence based on hand confidence, object confidence, and hysteresis maturity
            hand_conf = cand.hand.confidence
            obj_conf = cand.obj.confidence
            base_conf = (hand_conf + obj_conf) / 2.0
            # Boost confidence if state has persisted
            maturity_factor = min(1.0, 0.7 + 0.3 * (tracklet.frames_in_state / 5.0))
            obs_confidence = max(0.0, min(1.0, base_conf * maturity_factor))

            observations.append(
                InteractionObservation(
                    hand_id=cand.hand.hand_id,
                    object_id=cand.obj.object_id,
                    person_track_id=cand.hand.person_track_id,
                    state=new_state,
                    distance_normalized=cand.features.normalized_distance,
                    overlap_ratio=cand.features.overlap_ratio,
                    approach_velocity=cand.features.approach_velocity,
                    contact_persistence_frames=tracklet.contact_persistence_frames,
                    confidence=obs_confidence,
                )
            )

        # Handle unseen existing tracklets (LOST / PRUNE)
        pairs_to_remove: list[tuple[str, str]] = []
        for pair_key, tracklet in self._tracklets.items():
            if pair_key not in seen_pairs:
                frames_missing = frame_index - tracklet.last_seen_frame
                if frames_missing > self.prune_after_frames:
                    pairs_to_remove.append(pair_key)
                elif frames_missing > self.max_lost_frames:
                    tracklet.current_state = InteractionState.LOST
                    tracklet.frames_in_state += 1
                    tracklet.contact_persistence_frames = 0
                else:
                    # Transient unobserved frame, retain prior state or transition to RELEASING
                    if tracklet.current_state in (InteractionState.GRASPING, InteractionState.MANIPULATING):
                        tracklet.current_state = InteractionState.RELEASING
                    tracklet.frames_in_state += 1

        for pair_key in pairs_to_remove:
            self._tracklets.pop(pair_key, None)
            self._prev_distances.pop(pair_key, None)

        return observations

    def _evaluate_transition(
        self,
        tracklet: PairTracklet,
        cand: HandObjectCandidate,
        frame_index: int,
    ) -> InteractionState:
        curr = tracklet.current_state
        feat = cand.features

        # 1. Contact / Grasping / Manipulating conditions
        if feat.is_in_contact:
            if tracklet.contact_persistence_frames >= self.min_grasp_frames:
                # Check for manipulation evidence: sustained grasp + object displacement or motion
                if curr == InteractionState.MANIPULATING:
                    return InteractionState.MANIPULATING
                if curr == InteractionState.GRASPING:
                    # If sustained contact in grasp state exceeds min_manipulate_frames
                    if tracklet.frames_in_state >= self.min_manipulate_frames:
                        return InteractionState.MANIPULATING
                    return InteractionState.GRASPING
                return InteractionState.GRASPING
            return InteractionState.CONTACT

        # 2. Moving away while previously in Grasp / Manipulate
        if curr in (InteractionState.GRASPING, InteractionState.MANIPULATING, InteractionState.CONTACT):
            if not feat.is_in_contact:
                return InteractionState.RELEASING

        if curr == InteractionState.RELEASING:
            if tracklet.frames_in_state >= self.min_release_frames:
                return InteractionState.NEAR if feat.is_near else InteractionState.NO_INTERACTION
            return InteractionState.RELEASING

        # 3. Near / Approaching
        if feat.is_near:
            if feat.approach_velocity > 0.005 and tracklet.consecutive_near_frames >= self.min_approach_frames:
                return InteractionState.APPROACHING
            return InteractionState.NEAR

        return InteractionState.NO_INTERACTION
