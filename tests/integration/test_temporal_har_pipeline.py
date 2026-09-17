"""Integration test for the full end-to-end perception + temporal HAR pipeline.

Verifies:
VIDEO INPUT -> FRAME ACQUISITION -> OBJECT DETECTION -> BYTE TRACKING
-> POSE ESTIMATION -> TEMPORAL HAR (ST-GCN) -> STRUCTURED OBSERVATION
-> IN-MEMORY EVENT BUS -> SQLITE PERSISTENCE
"""

from pathlib import Path

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
)
from orion_ai.activity.configs import ActivityConfig
from orion_ai.activity.runtime import TemporalHARRuntime
from orion_ai.activity.schemas import TRAINED_ACTIVITY_CLASSES
from orion_ai.camera.opencv_driver import OpenCVCameraDriver
from orion_ai.detection.yolo_detector import YOLOEdgeDetector
from orion_ai.pose.yolo_pose import YOLOPoseEstimator
from orion_ai.runtime.coordinator import PerceptionPipelineCoordinator
from orion_ai.runtime.observation import StructuredObservation
from orion_ai.tracking.byte_tracker import ByteTracker


@pytest.mark.asyncio
@pytest.mark.integration
async def test_end_to_end_temporal_har_pipeline(test_engine: AsyncEngine) -> None:
    """Run 35 real frames through optical perception + ST-GCN temporal HAR."""
    video_path = Path("assets/sample_replay.mp4")
    assert video_path.exists(), "Sample replay video must exist"
    det_weights = Path("models/weights/yolo11n.pt")
    assert det_weights.exists(), "YOLO11n weights must exist"
    pose_weights = Path("models/weights/yolo11n-pose.pt")
    assert pose_weights.exists(), "YOLO11n-pose weights must exist"
    har_weights = Path("models/weights/stgcn_har_v1.pt")
    assert har_weights.exists(), "ST-GCN weights must exist"

    # 1. Initialize Event Bus and SQLite Persistence Subscriber
    event_bus = InMemoryEventBus()
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    persistence_subscriber = EventPersistenceSubscriber(session_factory=session_factory)
    await persistence_subscriber.start()

    event_bus.subscribe(BaseEvent, persistence_subscriber.on_event)

    captured_events: list[BaseEvent] = []

    async def audit_listener(evt: BaseEvent) -> None:
        captured_events.append(evt)

    event_bus.subscribe(BaseEvent, audit_listener)

    # 2. Instantiate AI Hardware & Model Components
    camera = OpenCVCameraDriver(
        source=str(video_path),
        camera_id="bas_optical_test",
        target_fps=0,
        width=640,
        height=480,
        loop=True,
    )
    detector = YOLOEdgeDetector(confidence_threshold=0.25, device="cpu")
    pose_estimator = YOLOPoseEstimator(confidence_threshold=0.25, device="cpu")
    tracker = ByteTracker(high_score_thresh=0.4, match_thresh=0.3)

    har_config = ActivityConfig(
        model_id="stgcn_har_v1",
        window_size_frames=32,
        stride_frames=8,
        confidence_threshold=0.3,
    )
    har_runtime = TemporalHARRuntime(
        config=har_config,
        model_path=str(har_weights),
        device="cpu",
        station_id="BAS-TEST-STATION",
    )

    # 3. Load Models and Initialize Camera
    await camera.initialize()
    await detector.load(str(det_weights))
    await pose_estimator.load(str(pose_weights))
    await har_runtime.initialize()

    # 4. Construct Coordinator
    coordinator = PerceptionPipelineCoordinator(
        camera=camera,
        detector=detector,
        pose_estimator=pose_estimator,
        tracker=tracker,
        event_bus=event_bus,
        station_id="BAS-TEST-STATION",
        har_runtime=har_runtime,
    )

    # 5. Process 35 frames sequentially (triggering 32-frame HAR window)
    observations: list[StructuredObservation] = []
    for _ in range(35):
        obs = await coordinator.process_single_frame()
        observations.append(obs)

    # 6. Verify Structured Observations
    assert len(observations) == 35
    for idx, obs in enumerate(observations, start=1):
        assert obs.frame_index == idx
        assert obs.station_id == "BAS-TEST-STATION"
        assert obs.pipeline_status == "NOMINAL"
        assert obs.metrics.detection_latency_ms > 0
        assert obs.metrics.pose_latency_ms > 0
        assert obs.metrics.pipeline_latency_ms > 0

    # Frames >= 32 must evaluate temporal HAR
    later_obs = observations[31:]
    assert any(len(obs.activities) > 0 for obs in later_obs), (
        "At least one frame >= 32 must have recognized activities"
    )

    for obs in later_obs:
        if obs.activities:
            assert obs.top_activity is not None
            assert obs.top_activity.activity_name in TRAINED_ACTIVITY_CLASSES
            assert obs.metrics.har_latency_ms >= 0.0

    # 7. Verify In-Memory Event Bus Dispatched Events
    frame_events = [e for e in captured_events if isinstance(e, FrameCaptured)]
    det_events = [e for e in captured_events if isinstance(e, DetectionCompleted)]
    pose_events = [e for e in captured_events if isinstance(e, PoseCompleted)]
    har_events = [e for e in captured_events if isinstance(e, ActivityRecognized)]

    assert len(frame_events) == 35
    assert len(det_events) == 35
    assert len(pose_events) == 35
    assert len(har_events) >= 1, "At least one ActivityRecognized event must be emitted"
    assert har_events[0].activity_label in TRAINED_ACTIVITY_CLASSES

    # 8. Verify SQLite Persistence
    await persistence_subscriber.stop()

    async with session_factory() as session:
        result = await session.execute(select(Event))
        persisted_events = result.scalars().all()
        assert len(persisted_events) >= 105, (
            f"Expected at least 105 persisted events, got {len(persisted_events)}"
        )
        event_types = {e.event_type for e in persisted_events}
        assert "FrameCaptured" in event_types
        assert "DetectionCompleted" in event_types
        assert "PoseCompleted" in event_types
        assert "ActivityRecognized" in event_types

    # 9. Clean Shutdown
    await camera.shutdown()
    await detector.unload()
    await pose_estimator.unload()
    await har_runtime.shutdown()
    await event_bus.shutdown()
