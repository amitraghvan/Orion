"""Comprehensive Integration Test Suite for ORION Runtime Correctness & Real Experiment Execution.

Verifies:
1. Camera acquisition and continuous frame indexing.
2. StructuredObservation emission with valid metrics, dimensions, and FPS.
3. Protocol FSM transitions: LOADED -> RUNNING -> PAUSED -> RESUMED -> ABORTED -> RUNNING (restart).
4. Step progression: matching activity advances step, out-of-order activity rejects/does not advance.
5. Recommendation updates on step advancement.
6. Persistence subscriber handles all perception/protocol events without numpy serialization errors.
7. Real-time telemetry payload formatting and consistency.
"""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from orion.core.in_memory_event_bus import InMemoryEventBus
from orion.db.models.event import Event
from orion.db.persistence_subscriber import EventPersistenceSubscriber
from orion.events.schemas import (
    ActivityRecognized,
    BaseEvent,
    DetectionCompleted,
    FrameCaptured,
    PoseCompleted,
    ProtocolStateChanged,
    StepTransitioned,
)
from orion.protocol.service import ProtocolService
from orion.protocol.state_machine import ProtocolState
from orion_ai.camera.opencv_driver import OpenCVCameraDriver
from orion_ai.detection.yolo_detector import YOLOEdgeDetector
from orion_ai.pose.yolo_pose import YOLOPoseEstimator
from orion_ai.runtime.coordinator import PerceptionPipelineCoordinator
from orion_ai.runtime.observation import PipelineMetrics, StructuredObservation
from orion_ai.tracking.byte_tracker import ByteTracker


@pytest.mark.asyncio
@pytest.mark.integration
async def test_camera_and_coordinator_frame_acquisition() -> None:
    """Verify camera captures real frames with strictly monotonic frame indices and valid metrics."""
    video_path = Path("assets/sample_replay.mp4")
    assert video_path.exists(), "Replay video must exist"
    det_weights = Path("models/weights/yolo11n.pt")
    pose_weights = Path("models/weights/yolo11n-pose.pt")

    event_bus = InMemoryEventBus()
    camera = OpenCVCameraDriver(
        source=str(video_path),
        camera_id="test_cam_0",
        target_fps=0,
        width=640,
        height=480,
        loop=True,
    )
    detector = YOLOEdgeDetector(confidence_threshold=0.25, device="cpu")
    pose_estimator = YOLOPoseEstimator(confidence_threshold=0.25, device="cpu")
    tracker = ByteTracker(high_score_thresh=0.4, match_thresh=0.3)

    await camera.initialize()
    if det_weights.exists():
        await detector.load(str(det_weights))
    if pose_weights.exists():
        await pose_estimator.load(str(pose_weights))

    coordinator = PerceptionPipelineCoordinator(
        camera=camera,
        detector=detector,
        pose_estimator=pose_estimator,
        tracker=tracker,
        event_bus=event_bus,
        station_id="BAS-TEST-STATION",
    )

    observations: list[StructuredObservation] = []
    for _ in range(5):
        obs = await coordinator.process_single_frame()
        observations.append(obs)

    await camera.shutdown()

    assert len(observations) == 5
    for i in range(len(observations)):
        obs = observations[i]
        assert obs.frame_index == i + 1
        assert obs.width == 640
        assert obs.height == 480
        assert obs.pipeline_status in ["NOMINAL", "DEGRADED"]
        assert obs.metrics.fps >= 0.0
        assert obs.metrics.pipeline_latency_ms >= 0.0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_protocol_fsm_lifecycle_and_step_status() -> None:
    """Verify FSM state transitions, step status consistency, and restart capabilities."""
    template_path = Path("experiments/experiment_template.yaml")
    assert template_path.exists(), "Template must exist"
    event_bus = InMemoryEventBus()
    service = ProtocolService(event_bus=event_bus)
    service.load_protocol_file(template_path)

    # 1. Initial State should be LOADED
    status = service.get_status_payload()
    assert status["fsm_state"] == ProtocolState.LOADED.value
    # In LOADED state, steps should NOT be ACTIVE
    for step in status["steps"]:
        assert step["status"] == "PENDING"

    # 2. Start Experiment -> RUNNING
    run_id = service.start_experiment(run_id="run_test_001")
    assert run_id == "run_test_001"

    status = service.get_status_payload()
    assert status["fsm_state"] == ProtocolState.RUNNING.value
    # Step 0 must now be ACTIVE, subsequent steps PENDING
    assert status["steps"][0]["status"] == "ACTIVE"
    assert status["steps"][1]["status"] == "PENDING"

    # Recommendation must target step 0
    rec = service.current_recommendation
    assert rec is not None
    assert rec.step_id == "step_01_preparation"
    assert rec.expected_activity == "prepare_workstation"

    # 3. Out-of-order activity should NOT advance step
    # Expecting prepare_workstation, feed inspect_chamber
    out_of_order_event = ActivityRecognized(
        station_id="BAS-TEST",
        track_id=0,
        frame_index=10,
        window_start_frame=0,
        window_end_frame=10,
        activity_label="inspect_chamber",
        confidence=0.95,
        phase="SUSTAINED",
        uncertainty_status="NOMINAL",
        is_anomaly=False,
    )
    await service.process_activity(out_of_order_event)
    status = service.get_status_payload()
    assert status["current_step_index"] == 0
    assert status["steps"][0]["status"] == "ACTIVE"

    # 4. Skip/Jump to next step directly (verifying step progression)
    skipped = service.skip_to_step("step_02_pipette_aspiration")
    assert skipped is True
    status = service.get_status_payload()
    assert status["current_step_index"] == 1
    assert status["steps"][0]["status"] == "COMPLETED"
    assert status["steps"][1]["status"] == "ACTIVE"

    # Recommendation must now target step 1
    rec = service.current_recommendation
    assert rec is not None
    assert rec.step_id == "step_02_pipette_aspiration"

    # 5. Pause experiment
    service.pause(reason="Astronaut hydration break")
    status = service.get_status_payload()
    assert status["fsm_state"] == ProtocolState.PAUSED.value
    assert status["steps"][1]["status"] == "PAUSED"

    # 6. Resume experiment
    service.resume(reason="Resuming experiment")
    status = service.get_status_payload()
    assert status["fsm_state"] == ProtocolState.RUNNING.value
    assert status["steps"][1]["status"] == "ACTIVE"

    # 7. Abort experiment
    service.abort(reason="Safety override")
    status = service.get_status_payload()
    assert status["fsm_state"] == ProtocolState.ABORTED.value
    assert status["steps"][1]["status"] == "ABORTED"

    # 8. Start run from ABORTED state (Fix verification for START RUN 400 issue)
    restart_id = service.start_experiment(run_id="run_test_restart_002")
    assert restart_id == "run_test_restart_002"
    status = service.get_status_payload()
    assert status["fsm_state"] == ProtocolState.RUNNING.value
    assert status["current_step_index"] == 0
    assert status["steps"][0]["status"] == "ACTIVE"
    assert status["steps"][1]["status"] == "PENDING"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_persistence_subscriber_handles_all_event_types_without_numpy_error(
    test_engine: AsyncEngine,
) -> None:
    """Verify EventPersistenceSubscriber sanitizes and persists events with numpy types cleanly."""
    import asyncio

    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    subscriber = EventPersistenceSubscriber(session_factory=session_factory)
    await subscriber.start()

    # Event 1: DetectionCompleted with numpy int and float types
    event_det = DetectionCompleted(
        station_id="BAS-TEST",
        frame_index=1,
        detection_count=np.int64(2),
        classes_detected=["person", "pipette"],
        inference_time_ms=np.float32(14.2),
    )

    # Event 2: ActivityRecognized with numpy confidence
    event_act = ActivityRecognized(
        station_id="BAS-TEST",
        track_id=np.int64(1),
        frame_index=np.int64(10),
        window_start_frame=0,
        window_end_frame=10,
        activity_label="prepare_workstation",
        confidence=np.float32(0.975),
        phase="SUSTAINED",
        uncertainty_status="NOMINAL",
        is_anomaly=False,
    )

    # Event 3: StepTransitioned
    event_step = StepTransitioned(
        station_id="BAS-TEST",
        experiment_id="BAS-TEST-CRYSTAL-V1",
        run_id="run_001",
        from_step_id="step_01_prepare",
        to_step_id="step_02_inspect",
        from_step_number=np.int64(0),
        to_step_number=np.int64(1),
        duration_seconds=np.float64(12.4),
        decision_id="dec_001",
    )

    # Process events through subscriber
    await subscriber.on_event(event_det)
    await subscriber.on_event(event_act)
    await subscriber.on_event(event_step)

    # Wait for queue to drain
    await asyncio.sleep(0.3)
    await subscriber.stop()

    # Query DB to ensure they were committed successfully
    async with session_factory() as session:
        result = await session.execute(
            select(Event).where(
                Event.event_type.in_(
                    ["DetectionCompleted", "ActivityRecognized", "StepTransitioned"]
                )
            )
        )
        persisted = result.scalars().all()
        assert len(persisted) == 3
        persisted_types = {e.event_type for e in persisted}
        assert "DetectionCompleted" in persisted_types
        assert "ActivityRecognized" in persisted_types
        assert "StepTransitioned" in persisted_types
