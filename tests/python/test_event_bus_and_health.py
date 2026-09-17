"""Tests for EventBus canonical event pub/sub and 13-subsystem Health Monitoring."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.core.event_bus import EventBus

from orion.events.schemas import (
    ActionRecognized,
    ExperimentCompleted,
    ExperimentFailed,
    ExperimentStarted,
    FrameCaptured,
    HandDetected,
    InteractionDetected,
    ObjectDetected,
    ObservationCaptured,
    PoseDetected,
    RecordingStarted,
    RecordingStopped,
    StepCompleted,
    StepStarted,
    StepViolation,
    VoiceRequested,
)
from orion.health.interfaces import SubsystemReport, SubsystemStatus
from orion_ai.camera.camera_manager import authoritative_camera_manager


def test_canonical_event_bus_pub_sub():
    """Verify all 16 Section 11 domain events are properly dispatched and received."""
    bus = EventBus()
    received_events: list[str] = []

    # Handlers for canonical events
    def on_frame(ev: FrameCaptured):
        received_events.append(ev.event_type)

    def on_obs(ev: ObservationCaptured):
        received_events.append(ev.event_type)

    def on_obj(ev: ObjectDetected):
        received_events.append(ev.event_type)

    def on_pose(ev: PoseDetected):
        received_events.append(ev.event_type)

    def on_hand(ev: HandDetected):
        received_events.append(ev.event_type)

    def on_interaction(ev: InteractionDetected):
        received_events.append(ev.event_type)

    def on_action(ev: ActionRecognized):
        received_events.append(ev.event_type)

    def on_step_start(ev: StepStarted):
        received_events.append(ev.event_type)

    def on_step_complete(ev: StepCompleted):
        received_events.append(ev.event_type)

    def on_step_violation(ev: StepViolation):
        received_events.append(ev.event_type)

    def on_exp_start(ev: ExperimentStarted):
        received_events.append(ev.event_type)

    def on_exp_complete(ev: ExperimentCompleted):
        received_events.append(ev.event_type)

    def on_exp_fail(ev: ExperimentFailed):
        received_events.append(ev.event_type)

    def on_voice(ev: VoiceRequested):
        received_events.append(ev.event_type)

    def on_rec_start(ev: RecordingStarted):
        received_events.append(ev.event_type)

    def on_rec_stop(ev: RecordingStopped):
        received_events.append(ev.event_type)

    # Subscribe all
    bus.subscribe(FrameCaptured, on_frame)
    bus.subscribe(ObservationCaptured, on_obs)
    bus.subscribe(ObjectDetected, on_obj)
    bus.subscribe(PoseDetected, on_pose)
    bus.subscribe(HandDetected, on_hand)
    bus.subscribe(InteractionDetected, on_interaction)
    bus.subscribe(ActionRecognized, on_action)
    bus.subscribe(StepStarted, on_step_start)
    bus.subscribe(StepCompleted, on_step_complete)
    bus.subscribe(StepViolation, on_step_violation)
    bus.subscribe(ExperimentStarted, on_exp_start)
    bus.subscribe(ExperimentCompleted, on_exp_complete)
    bus.subscribe(ExperimentFailed, on_exp_fail)
    bus.subscribe(VoiceRequested, on_voice)
    bus.subscribe(RecordingStarted, on_rec_start)
    bus.subscribe(RecordingStopped, on_rec_stop)

    # Publish all 16 events
    bus.publish(
        FrameCaptured(
            camera_id="c1",
            frame_index=1,
            width=1280,
            height=720,
            pixel_format="BGR8",
            timestamp_sensor_ns=100,
            latency_ms=2.0,
        )
    )
    bus.publish(ObservationCaptured(observation={"frame": 1}))
    bus.publish(ObjectDetected(frame_index=1, object_count=2, classes=["person", "vial"]))
    bus.publish(PoseDetected(frame_index=1, person_count=1))
    bus.publish(HandDetected(frame_index=1, hand_count=2))
    bus.publish(
        InteractionDetected(
            frame_index=1, interaction_type="grasping", hand_id="h1", object_id="o1", confidence=0.9
        )
    )
    bus.publish(ActionRecognized(action="mix_solution", confidence=0.95, temporal_window=(1, 32)))
    bus.publish(StepStarted(experiment_id="E01", run_id="r1", step_id="s1", step_number=1))
    bus.publish(
        StepCompleted(
            experiment_id="E01", run_id="r1", step_id="s1", step_number=1, duration_seconds=12.0
        )
    )
    bus.publish(
        StepViolation(
            experiment_id="E01",
            run_id="r1",
            step_id="s1",
            step_number=1,
            violation_type="WRONG_OBJECT",
            message="Wrong object",
        )
    )
    bus.publish(ExperimentStarted(experiment_id="E01", run_id="r1"))
    bus.publish(
        ExperimentCompleted(
            experiment_id="E01", run_id="r1", total_duration_seconds=60.0, total_steps=5
        )
    )
    bus.publish(
        ExperimentFailed(
            experiment_id="E01", run_id="r1", error_code="ERR_STEP_TIMEOUT", reason="Timeout"
        )
    )
    bus.publish(VoiceRequested(message="Please verify chemical seal", priority="HIGH"))
    bus.publish(
        RecordingStarted(
            recording_id="rec_01",
            experiment_id="E01",
            file_path="/tmp/rec.mp4",
            resolution=(1280, 720),
            fps=30,
        )
    )
    bus.publish(
        RecordingStopped(
            recording_id="rec_01",
            file_path="/tmp/rec.mp4",
            duration_seconds=60.0,
            total_frames=1800,
            sha256_checksum="abc123hash",
        )
    )

    expected_events = [
        "FrameCaptured",
        "ObservationCaptured",
        "ObjectDetected",
        "PoseDetected",
        "HandDetected",
        "InteractionDetected",
        "ActionRecognized",
        "StepStarted",
        "StepCompleted",
        "StepViolation",
        "ExperimentStarted",
        "ExperimentCompleted",
        "ExperimentFailed",
        "VoiceRequested",
        "RecordingStarted",
        "RecordingStopped",
    ]
    assert received_events == expected_events


@pytest.mark.asyncio
async def test_subsystem_health_monitoring():
    """Verify real health status evaluation across all 13 canonical subsystems."""
    from orion.api.routers.health import _evaluate_system_health
    from orion.core.config import get_settings

    settings = get_settings()
    overall_status, details, subsystem_reports, trust_score = await _evaluate_system_health(
        settings=settings,
        db=None,
    )

    # Verify all 13 subsystems are accounted for in details and subsystem_reports
    canonical_13 = [
        "camera",
        "ai",
        "object_detection",
        "pose",
        "hand",
        "hoi",
        "har",
        "fsm",
        "database",
        "voice",
        "recording",
        "streaming",
        "compute",
    ]

    for sub in canonical_13:
        assert hasattr(details, sub), f"details missing attribute '{sub}'"
        assert sub in subsystem_reports, f"subsystem_reports missing '{sub}'"
        report = subsystem_reports[sub]
        assert isinstance(report, SubsystemReport)
        assert report.status in SubsystemStatus

    # Confirm truthfulness: compute backend is truthfully reported
    compute_rep = subsystem_reports["compute"]
    assert "backend" in compute_rep.details
    assert compute_rep.details["backend"] in ("MPS", "CUDA", "CPU")
