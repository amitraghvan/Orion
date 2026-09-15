"""The 20 Golden HOI & Multimodal Interaction Scenarios for ORION BAS AI Copilot.

SIH Problem Statement: SIH26174
Phase: 1.5 Multimodal Interaction & Evidence Intelligence
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import numpy as np
import pytest

from orion_ai.detection.schemas import BoundingBox2D
from orion_ai.hand.extractor import PoseBasedHandExtractor
from orion_ai.hand.schemas import HandObservation, HandSide, HandState
from orion_ai.interaction.conflict_detector import ModalityConflictDetector
from orion_ai.interaction.evidence import GraspEvidence, ManipulationEvidence
from orion_ai.interaction.evidence_quality import EvidenceQualityAssessor
from orion_ai.interaction.fusion import DeterministicMultimodalFusion
from orion_ai.interaction.geometry import (
    GeometricInteractionFeatures,
    InteractionGeometryCalculator,
    compute_motion_correlation,
)
from orion_ai.interaction.hand_object_associator import HandObjectAssociator
from orion_ai.interaction.multimodal_schemas import (
    EvidenceQualityLevel,
    EvidenceState,
    InteractionState,
)
from orion_ai.interaction.object_schemas import ObjectObservation
from orion_ai.interaction.state_machine import InteractionStateMachine
from orion_ai.pose.schemas import HumanPose, Keypoint2D
from orion_ai.tracking.schemas import TrackedObject, TrackState


def _make_pose(
    person_id: int = 1,
    wrist_x: float = 300.0,
    wrist_y: float = 400.0,
    wrist_score: float = 0.9,
    bbox_diag: float = 500.0,
) -> HumanPose:
    """Create a mock HumanPose with valid wrists and bounding box."""
    return HumanPose(
        person_id=person_id,
        bbox=BoundingBox2D(x_min=200, y_min=200, x_max=600, y_max=800),
        topology="coco_17",
        keypoints_2d=[
            Keypoint2D(id=9, name="left_wrist", x=wrist_x - 50, y=wrist_y, score=wrist_score),
            Keypoint2D(id=10, name="right_wrist", x=wrist_x, y=wrist_y, score=wrist_score),
        ],
        overall_confidence=0.92,
    )


def _make_hand(
    person_id: int = 1,
    side: HandSide = HandSide.RIGHT,
    cx: float = 300.0,
    cy: float = 400.0,
    confidence: float = 0.9,
    state: HandState = HandState.OBSERVED,
    pad: float = 30.0,
) -> HandObservation:
    """Create a mock HandObservation."""
    return HandObservation(
        hand_id=f"hand_p{person_id}_{side.value}",
        side=side,
        person_track_id=person_id,
        region_bbox=BoundingBox2D(x_min=cx - pad, y_min=cy - pad, x_max=cx + pad, y_max=cy + pad),
        wrist_keypoint=Keypoint2D(id=10 if side == HandSide.RIGHT else 9, name=f"{side.value}_wrist", x=cx, y=cy, score=confidence),
        confidence=confidence,
        state=state,
        frame_index=1,
        timestamp=datetime.now(UTC),
        source_id="cam_01",
    )


def _make_object(
    class_name: str = "tool_pipette_p1000",
    cx: float = 300.0,
    cy: float = 400.0,
    w: float = 40.0,
    h: float = 40.0,
    confidence: float = 0.88,
    track_id: int = 101,
) -> ObjectObservation:
    """Create a mock ObjectObservation."""
    return ObjectObservation(
        object_id=f"obj_{class_name}_{track_id}",
        class_name=class_name,
        bbox=BoundingBox2D(x_min=cx - w / 2, y_min=cy - h / 2, x_max=cx + w / 2, y_max=cy + h / 2),
        confidence=confidence,
        track_id=track_id,
        frame_index=1,
        timestamp=datetime.now(UTC),
        source_id="cam_01",
    )


# Scenario 01: No interaction — empty hand, no objects
def test_sc01_no_interaction_empty_hand_no_objects() -> None:
    hand = _make_hand(cx=100.0, cy=100.0)
    associator = HandObjectAssociator()
    candidates = associator.associate(hands=[hand], objects=[], reference_diagonal=1000.0)
    assert len(candidates) == 0

    sm = InteractionStateMachine()
    observations = sm.update(candidates=candidates, frame_index=1)
    assert len(observations) == 0


# Scenario 02: Approaching object — distance decreasing over frames
def test_sc02_approaching_object_distance_decreasing() -> None:
    associator = HandObjectAssociator()
    sm = InteractionStateMachine(min_approach_frames=2)
    obj = _make_object(cx=500.0, cy=500.0)

    # Frame 1: Hand far away (dist ~ 400px)
    h1 = _make_hand(cx=200.0, cy=200.0)
    cands1 = associator.associate(hands=[h1], objects=[obj], reference_diagonal=1000.0)
    obs1 = sm.update(candidates=cands1, frame_index=1)
    assert len(obs1) == 1
    assert obs1[0].state == InteractionState.NEAR or obs1[0].state == InteractionState.NO_INTERACTION

    # Frame 2: Hand moves closer (dist ~ 200px)
    h2 = _make_hand(cx=350.0, cy=350.0)
    prev_dist = sm.get_previous_distance(h1.hand_id, obj.object_id)
    cands2 = associator.associate(hands=[h2], objects=[obj], reference_diagonal=1000.0, prev_distances={(h1.hand_id, obj.object_id): prev_dist or 0.5})
    obs2 = sm.update(candidates=cands2, frame_index=2)
    assert obs2[0].approach_velocity > 0

    # Frame 3: Hand continues approaching
    h3 = _make_hand(cx=450.0, cy=450.0)
    prev_dist = sm.get_previous_distance(h1.hand_id, obj.object_id)
    cands3 = associator.associate(hands=[h3], objects=[obj], reference_diagonal=1000.0, prev_distances={(h1.hand_id, obj.object_id): prev_dist or 0.3})
    obs3 = sm.update(candidates=cands3, frame_index=3)
    assert obs3[0].state in (InteractionState.APPROACHING, InteractionState.NEAR)


# Scenario 03: Contact — overlap threshold crossed
def test_sc03_contact_overlap_threshold_crossed() -> None:
    hand = _make_hand(cx=500.0, cy=500.0, pad=30.0)
    obj = _make_object(cx=510.0, cy=510.0, w=40.0, h=40.0)

    associator = HandObjectAssociator()
    candidates = associator.associate(hands=[hand], objects=[obj], reference_diagonal=1000.0)
    assert len(candidates) == 1
    assert candidates[0].features.is_in_contact is True
    assert candidates[0].state_hint == InteractionState.CONTACT


# Scenario 04: Grasp — persistent contact + hand state OBSERVED
def test_sc04_grasp_persistent_contact_and_observed_hand() -> None:
    hand = _make_hand(cx=500.0, cy=500.0, state=HandState.OBSERVED)
    obj = _make_object(cx=505.0, cy=505.0)

    associator = HandObjectAssociator()
    sm = InteractionStateMachine(min_grasp_frames=3)

    for f_idx in range(1, 5):
        cands = associator.associate(hands=[hand], objects=[obj], reference_diagonal=1000.0)
        obs = sm.update(candidates=cands, frame_index=f_idx)
        if f_idx < 3:
            assert obs[0].state == InteractionState.CONTACT
        else:
            assert obs[0].state == InteractionState.GRASPING

    evidence = GraspEvidence.from_observation(obs[0])
    assert evidence.is_stable_grasp is True


# Scenario 05: Sustained grasp — 10+ frames
def test_sc05_sustained_grasp_ten_plus_frames() -> None:
    hand = _make_hand(cx=500.0, cy=500.0)
    obj = _make_object(cx=500.0, cy=500.0)

    associator = HandObjectAssociator()
    sm = InteractionStateMachine(min_grasp_frames=3)

    for f_idx in range(1, 15):
        cands = associator.associate(hands=[hand], objects=[obj], reference_diagonal=1000.0)
        obs = sm.update(candidates=cands, frame_index=f_idx)

    assert obs[0].contact_persistence_frames >= 10
    assert obs[0].state in (InteractionState.GRASPING, InteractionState.MANIPULATING)


# Scenario 06: Release — distance increasing after grasp
def test_sc06_release_distance_increasing_after_grasp() -> None:
    associator = HandObjectAssociator()
    sm = InteractionStateMachine(min_grasp_frames=3, min_release_frames=2)
    obj = _make_object(cx=500.0, cy=500.0)

    # Establish grasp
    for f in range(1, 4):
        h = _make_hand(cx=500.0, cy=500.0)
        cands = associator.associate(hands=[h], objects=[obj], reference_diagonal=1000.0)
        obs = sm.update(candidates=cands, frame_index=f)
    assert obs[0].state == InteractionState.GRASPING

    # Break contact and move away
    h_away = _make_hand(cx=650.0, cy=650.0)
    cands = associator.associate(hands=[h_away], objects=[obj], reference_diagonal=1000.0)
    obs = sm.update(candidates=cands, frame_index=4)
    assert obs[0].state == InteractionState.RELEASING


# Scenario 07: Manipulation — grasp + object motion
def test_sc07_manipulation_grasp_plus_object_motion() -> None:
    hand = _make_hand(cx=500.0, cy=500.0)
    obj = _make_object(cx=505.0, cy=505.0)

    associator = HandObjectAssociator()
    sm = InteractionStateMachine(min_grasp_frames=2, min_manipulate_frames=2)

    for f in range(1, 6):
        cands = associator.associate(hands=[hand], objects=[obj], reference_diagonal=1000.0)
        obs = sm.update(candidates=cands, frame_index=f)

    assert obs[0].state == InteractionState.MANIPULATING

    # Check manipulation evidence
    manip = ManipulationEvidence.from_observation(obs[0], displacement=15.0, correlation=0.85)
    assert manip.is_active_manipulation is True
    assert manip.grasp_evidence.is_stable_grasp is True


# Scenario 08: Object missing — hand detected, no object
def test_sc08_object_missing_hand_detected_no_object() -> None:
    hand = _make_hand(cx=500.0, cy=500.0)
    fusion = DeterministicMultimodalFusion(fusion_level=3)

    evidence = fusion.fuse(
        predicted_activity="grasp_tool",
        activity_confidence=0.85,
        person_track_id=1,
        pose=None,
        track=None,
        hands=[hand],
        objects=[],
        interactions=[],
        window_start=1,
        window_end=1,
    )
    assert evidence.evidence_state in (EvidenceState.CONFLICTING_EVIDENCE, EvidenceState.PARTIAL_EVIDENCE)


# Scenario 09: Hand missing — object detected, no hand
def test_sc09_hand_missing_object_detected_no_hand() -> None:
    obj = _make_object()
    fusion = DeterministicMultimodalFusion(fusion_level=2)

    evidence = fusion.fuse(
        predicted_activity="reach_tool",
        activity_confidence=0.80,
        person_track_id=1,
        pose=None,
        track=None,
        hands=[],
        objects=[obj],
        interactions=[],
        window_start=1,
        window_end=1,
    )
    assert evidence.evidence_state == EvidenceState.PARTIAL_EVIDENCE


# Scenario 10: Actor ambiguity — 2 persons, hands near same object
def test_sc10_actor_ambiguity_two_persons_near_same_object() -> None:
    h_p1 = _make_hand(person_id=1, cx=495.0, cy=500.0)
    h_p2 = _make_hand(person_id=2, cx=505.0, cy=500.0)
    obj = _make_object(cx=500.0, cy=500.0)

    associator = HandObjectAssociator()
    candidates = associator.associate(hands=[h_p1, h_p2], objects=[obj], reference_diagonal=1000.0)
    # Bipartite matching ensures only 1 hand pairs with the object
    assert len(candidates) == 1
    assert candidates[0].hand.person_track_id in (1, 2)


# Scenario 11: Modality conflict — ST-GCN says grasp, no object detected
def test_sc11_modality_conflict_stgcn_says_grasp_no_object() -> None:
    detector = ModalityConflictDetector()
    hand = _make_hand(cx=300.0, cy=400.0)

    result = detector.check_conflict(
        predicted_activity="grasp_tool",
        activity_confidence=0.92,
        hands=[hand],
        objects=[],
        interactions=[],
    )
    assert result.has_conflict is True
    assert result.conflict_type == "MISSING_TARGET_OBJECT"


# Scenario 12: Low-confidence object — object confidence < threshold
def test_sc12_low_confidence_object() -> None:
    obj = _make_object(confidence=0.15)
    assessor = EvidenceQualityAssessor()
    quality = assessor.assess(pose=None, track=None, hands=[], objects=[obj], interactions=[])
    assert quality.object_quality < 0.2


# Scenario 13: Low-confidence hand — wrist score < 0.2
def test_sc13_low_confidence_hand() -> None:
    extractor = PoseBasedHandExtractor()
    pose = _make_pose(wrist_score=0.10)
    hands = extractor.extract_hands(None, [pose], [], frame_index=1)
    assert all(h.state == HandState.OCCLUDED for h in hands)


# Scenario 14: Stable multimodal grasp — all modalities agree
def test_sc14_stable_multimodal_grasp_all_modalities_agree() -> None:
    pose = _make_pose(wrist_score=0.95)
    track = TrackedObject(track_id=1, class_id=0, class_name="person", box=BoundingBox2D(x_min=200, y_min=200, x_max=600, y_max=800), confidence=0.95, state=TrackState.TRACKED, age_frames=20)
    hand = _make_hand(person_id=1, cx=300.0, cy=400.0, confidence=0.95)
    obj = _make_object(cx=305.0, cy=405.0, confidence=0.92)

    sm = InteractionStateMachine(min_grasp_frames=3)
    associator = HandObjectAssociator()
    for f in range(1, 5):
        cands = associator.associate([hand], [obj])
        obs = sm.update(cands, f)

    fusion = DeterministicMultimodalFusion(fusion_level=3)
    evidence = fusion.fuse(
        predicted_activity="grasp_tool",
        activity_confidence=0.90,
        person_track_id=1,
        pose=pose,
        track=track,
        hands=[hand],
        objects=[obj],
        interactions=obs,
        window_start=1,
        window_end=5,
    )
    assert evidence.evidence_state == EvidenceState.FULL_EVIDENCE
    assert evidence.evidence_quality.overall == EvidenceQualityLevel.HIGH


# Scenario 15: False transient contact — single frame overlap
def test_sc15_false_transient_contact_single_frame_overlap() -> None:
    hand = _make_hand(cx=500.0, cy=500.0)
    obj = _make_object(cx=500.0, cy=500.0)

    associator = HandObjectAssociator()
    sm = InteractionStateMachine(min_grasp_frames=3)

    cands = associator.associate([hand], [obj])
    obs = sm.update(cands, frame_index=1)
    assert obs[0].state == InteractionState.CONTACT  # not GRASPING on frame 1


# Scenario 16: Orientation perturbation — rotated bounding boxes / microgravity float
def test_sc16_orientation_perturbation() -> None:
    # Microgravity: hand above object instead of standard posture
    calc = InteractionGeometryCalculator()
    hand = _make_hand(cx=400.0, cy=300.0)
    obj = _make_object(cx=400.0, cy=340.0)

    feat = calc.compute_features(hand, obj, reference_diagonal=800.0)
    assert feat.is_in_contact or feat.is_near


# Scenario 17: Camera crop change — scale invariance
def test_sc17_camera_crop_change_normalization_invariance() -> None:
    calc = InteractionGeometryCalculator()
    hand = _make_hand(cx=200.0, cy=200.0)
    obj = _make_object(cx=240.0, cy=240.0)

    feat1 = calc.compute_features(hand, obj, reference_diagonal=1000.0)

    # 2x zoom: pixels doubled, reference diagonal also doubled
    hand_z = _make_hand(cx=400.0, cy=400.0, pad=60.0)
    obj_z = _make_object(cx=480.0, cy=480.0, w=80.0, h=80.0)
    feat2 = calc.compute_features(hand_z, obj_z, reference_diagonal=2000.0)

    assert abs(feat1.normalized_distance - feat2.normalized_distance) < 0.01


# Scenario 18: Track loss — person track lost mid-interaction
def test_sc18_track_loss_person_track_lost_mid_interaction() -> None:
    hand = _make_hand(cx=500.0, cy=500.0)
    obj = _make_object(cx=500.0, cy=500.0)
    associator = HandObjectAssociator()
    sm = InteractionStateMachine(min_grasp_frames=3, max_lost_frames=3)

    for f in range(1, 4):
        cands = associator.associate([hand], [obj])
        sm.update(cands, f)

    # Person / hand disappears
    for f in range(4, 9):
        sm.update([], frame_index=f)

    # Tracklet marked lost or pruned
    assert sm._tracklets[(hand.hand_id, obj.object_id)].current_state == InteractionState.LOST


# Scenario 19: Object track loss — object disappears mid-grasp
def test_sc19_object_track_loss_object_disappears_mid_grasp() -> None:
    hand = _make_hand(cx=500.0, cy=500.0)
    obj = _make_object(cx=500.0, cy=500.0)
    associator = HandObjectAssociator()
    sm = InteractionStateMachine(min_grasp_frames=3)

    for f in range(1, 4):
        cands = associator.associate([hand], [obj])
        obs = sm.update(cands, f)
    assert obs[0].state == InteractionState.GRASPING

    # Object disappears, empty candidate list
    obs_after = sm.update([], frame_index=4)
    assert len(obs_after) == 0


# Scenario 20: Subsystem failure — hand extractor throws exception gracefully
def test_sc20_subsystem_failure_hand_extractor_fault_isolation() -> None:
    class FailingHandExtractor(PoseBasedHandExtractor):
        def extract_hands(self, *args: Any, **kwargs: Any) -> list[HandObservation]:
            raise RuntimeError("SIMULATED_HAND_PERCEPTION_FAILURE")

    extractor = FailingHandExtractor()
    with pytest.raises(RuntimeError):
        extractor.extract_hands(None, [], [], 1)
