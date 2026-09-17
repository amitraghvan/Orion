"""Tests for canonical StructuredObservation data contract."""

from datetime import UTC, datetime

from orion_ai.activity.schemas import ActivityPrediction, ActivityRecognitionResult
from orion_ai.detection.schemas import BoundingBox2D, DetectionTarget
from orion_ai.hand.schemas import HandObservation, HandSide
from orion_ai.interaction.multimodal_schemas import (
    InteractionObservation,
    InteractionState,
    MultimodalActivityEvidence,
)
from orion_ai.interaction.object_schemas import ObjectObservation
from orion_ai.pose.schemas import HumanPose, Keypoint2D
from orion_ai.runtime.observation import PipelineMetrics, StructuredObservation
from orion_ai.tracking.schemas import TrackedObject, TrackState


def test_canonical_structured_observation_creation():
    """Verify StructuredObservation conforms strictly to Section 10 canonical contract."""
    now = datetime.now(UTC)

    # Detections: 1 person, 1 vial
    person_det = DetectionTarget(
        class_id=0,
        class_name="person",
        confidence=0.92,
        box=BoundingBox2D(x_min=100.0, y_min=50.0, x_max=300.0, y_max=450.0),
    )
    vial_det = DetectionTarget(
        class_id=1,
        class_name="vial",
        confidence=0.88,
        box=BoundingBox2D(x_min=150.0, y_min=200.0, x_max=200.0, y_max=280.0),
    )

    # Pose: 17 keypoints
    kpts = [
        Keypoint2D(id=i, name=f"kpt_{i}", x=150.0 + i, y=100.0 + i, score=0.8) for i in range(17)
    ]
    pose = HumanPose(
        person_id=1,
        bbox=BoundingBox2D(x_min=100.0, y_min=50.0, x_max=300.0, y_max=450.0),
        keypoints_2d=kpts,
        overall_confidence=0.89,
    )

    # Tracks
    track = TrackedObject(
        track_id=1,
        class_id=0,
        class_name="person",
        box=BoundingBox2D(x_min=100.0, y_min=50.0, x_max=300.0, y_max=450.0),
        confidence=0.92,
        state=TrackState.TRACKED,
    )

    # Hands
    from orion_ai.hand.schemas import HandState

    hand = HandObservation(
        hand_id="hand_right_01",
        side=HandSide.RIGHT,
        person_track_id=1,
        region_bbox=BoundingBox2D(x_min=180.0, y_min=220.0, x_max=230.0, y_max=270.0),
        confidence=0.85,
        state=HandState.OBSERVED,
        frame_index=42,
        timestamp=now,
        source_id="live_camera",
    )

    # HOI
    interaction = InteractionObservation(
        hand_id="hand_right_01",
        object_id="vial_01",
        person_track_id=1,
        state=InteractionState.GRASPING,
        distance_normalized=0.05,
        overlap_ratio=0.6,
        confidence=0.91,
    )

    # HAR
    from orion_ai.activity.schemas import ActivityWindow

    har = ActivityRecognitionResult(
        track_id=1,
        window=ActivityWindow(start_frame=10, end_frame=42, fps=30),
        top_prediction=ActivityPrediction(
            activity_name="mix_solution",
            confidence=0.94,
        ),
    )

    # Evidence
    from orion_ai.interaction.multimodal_schemas import (
        EvidenceQuality,
        EvidenceQualityLevel,
        EvidenceState,
    )

    quality = EvidenceQuality(
        pose_quality=0.9,
        actor_identity_quality=0.9,
        hand_quality=0.85,
        object_quality=0.88,
        interaction_quality=0.91,
        temporal_stability=0.92,
        overall=EvidenceQualityLevel.HIGH,
    )

    evidence = MultimodalActivityEvidence(
        activity="mix_solution",
        person_track_id=1,
        hands=[hand],
        interactions=[interaction],
        confidence=0.93,
        evidence_quality=quality,
        evidence_state=EvidenceState.FULL_EVIDENCE,
        window_start=10,
        window_end=42,
    )

    # Metrics
    metrics = PipelineMetrics(
        camera_latency_ms=2.1,
        detection_latency_ms=12.4,
        pose_latency_ms=14.2,
        har_latency_ms=4.8,
        pipeline_latency_ms=33.5,
        fps=29.8,
        dropped_frames_total=0,
        compute_backend="MPS",
    )

    obs = StructuredObservation(
        station_id="BAS-NODE-01",
        frame_index=42,
        timestamp_utc=now,
        source_id="live_camera",
        width=1280,
        height=720,
        detections=[person_det, vial_det],
        poses=[pose],
        tracks=[track],
        hand_observations=[hand],
        object_observations=[
            ObjectObservation(
                object_id="vial_01",
                class_name="vial",
                bbox=BoundingBox2D(x_min=150.0, y_min=200.0, x_max=200.0, y_max=280.0),
                confidence=0.88,
                frame_index=42,
                timestamp=now,
                source_id="live_camera",
            )
        ],
        interaction_observations=[interaction],
        activities=[har],
        top_activity=har.top_prediction,
        multimodal_evidence=evidence,
        metrics=metrics,
        system_health={"camera": "HEALTHY", "ai": "HEALTHY", "compute": "HEALTHY"},
    )

    # Verify canonical alias accessors
    assert obs.frame_id == 42
    assert obs.timestamp == now
    assert len(obs.person_detections) == 1
    assert obs.person_detections[0].class_name == "person"
    assert len(obs.object_detections) == 1
    assert obs.object_detections[0].class_name == "vial"
    assert len(obs.poses) == 1
    assert len(obs.poses[0].keypoints) == 17
    assert len(obs.hands) == 1
    assert obs.hands[0].side == "right"
    assert len(obs.hand_object_interactions) == 1
    assert obs.hand_object_interactions[0].state == "grasping"
    assert obs.har_result is not None
    assert obs.har_result.activity == "mix_solution"
    assert obs.evidence is not None
    assert obs.evidence.confidence == 0.93
    assert obs.metrics.compute_backend == "MPS"
    assert obs.system_health["camera"] == "HEALTHY"

    # Verify zero base64 bloat
    assert obs.image_jpeg is None
    dump = obs.model_dump()
    assert "image_jpeg" in dump
    assert dump["image_jpeg"] is None
