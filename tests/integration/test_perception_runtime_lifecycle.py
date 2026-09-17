"""Integration tests for P0.1 — End-to-End Perception Runtime Integration.

Minimum required test coverage:
TEST 1: FastAPI lifespan starts the perception pipeline.
TEST 2: FastAPI shutdown stops the perception pipeline cleanly.
TEST 3: A generated Structured Observation enters the EventBus.
TEST 4: The WebSocket forwarding path receives the observation.
TEST 5: Frontend-facing telemetry JSON is serializable and contains the expected existing fields.
TEST 6: Pipeline failure is logged/handled without leaving unmanaged tasks.
TEST 7: No duplicate subscribers or duplicate WebSocket broadcasts are created when the application starts.
"""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from orion.api.app import create_app
from orion.api.routers.telemetry_ws import (
    WebSocketConnectionManager,
)
from orion.api.routers.telemetry_ws import (
    manager as ws_manager,
)
from orion.core.config import ApiSettings, CameraSettings, OrionSettings
from orion.core.in_memory_event_bus import InMemoryEventBus
from orion.di.container import (
    get_coordinator,
    get_event_bus,
)
from orion.events.schemas import (
    BaseEvent,
    DetectionCompleted,
    FrameCaptured,
    ObservationCaptured,
    PoseCompleted,
)
from orion_ai.camera.interfaces import CameraDriverInterface
from orion_ai.camera.schemas import CameraIntrinsics, FrameContract, Resolution
from orion_ai.detection.interfaces import DetectorInterface
from orion_ai.detection.schemas import BoundingBox2D, DetectionResult, DetectionTarget
from orion_ai.pose.interfaces import PoseEstimatorInterface
from orion_ai.pose.schemas import HumanPose, Keypoint2D, PoseEstimationResult
from orion_ai.runtime.coordinator import PerceptionPipelineCoordinator
from orion_ai.runtime.observation import PipelineMetrics, StructuredObservation
from orion_ai.tracking.byte_tracker import ByteTracker


class MockCameraDriver(CameraDriverInterface):
    """Deterministic in-memory camera driver producing mock frames."""

    def __init__(self, width: int = 640, height: int = 480) -> None:
        self.width = width
        self.height = height
        self.is_active = False
        self.frame_idx = 0
        self.dropped_frames = 0

    async def initialize(self) -> None:
        self.is_active = True

    async def shutdown(self) -> None:
        self.is_active = False

    async def read_frame(self) -> tuple[FrameContract, np.ndarray[Any, Any]]:
        if not self.is_active:
            raise RuntimeError("Camera not initialized")
        self.frame_idx += 1
        contract = FrameContract(
            camera_id="mock_cam_01",
            frame_index=self.frame_idx,
            resolution=Resolution(width=self.width, height=self.height),
            channels=3,
            pixel_format="BGR8",
            timestamp_utc=datetime.now(UTC),
            timestamp_sensor_ns=1000000 * self.frame_idx,
        )
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        return contract, frame

    def get_intrinsics(self) -> CameraIntrinsics:
        return CameraIntrinsics(
            fx=500.0,
            fy=500.0,
            cx=self.width / 2.0,
            cy=self.height / 2.0,
        )


class MockDetector(DetectorInterface):
    """Lightweight detector stub returning deterministic detection targets."""

    async def load(self, model_path: str) -> None:
        pass

    async def unload(self) -> None:
        pass

    async def detect(self, frame_buffer: np.ndarray[Any, Any], frame_index: int) -> DetectionResult:
        return DetectionResult(
            frame_index=frame_index,
            timestamp_sensor_ns=1000000 * frame_index,
            detections=[
                DetectionTarget(
                    class_id=0,
                    class_name="person",
                    confidence=0.95,
                    box=BoundingBox2D(x_min=100, y_min=100, x_max=300, y_max=400),
                )
            ],
            inference_latency_ms=5.0,
        )


class MockPoseEstimator(PoseEstimatorInterface):
    """Lightweight pose estimator stub returning 17-point skeletons."""

    async def load(self, model_path: str) -> None:
        pass

    async def unload(self) -> None:
        pass

    async def estimate(
        self, frame_buffer: np.ndarray[Any, Any], det_result: DetectionResult | None = None
    ) -> PoseEstimationResult:
        frame_idx = det_result.frame_index if det_result else 1
        return PoseEstimationResult(
            frame_index=frame_idx,
            poses=[
                HumanPose(
                    person_id=1,
                    bbox=BoundingBox2D(x_min=100, y_min=100, x_max=300, y_max=400),
                    topology="coco_17",
                    keypoints_2d=[
                        Keypoint2D(id=i, name=f"kpt_{i}", x=150.0 + i, y=150.0 + i, score=0.9)
                        for i in range(17)
                    ],
                    overall_confidence=0.92,
                )
            ],
            inference_time_ms=4.0,
        )


def _build_test_coordinator(bus: InMemoryEventBus) -> PerceptionPipelineCoordinator:
    return PerceptionPipelineCoordinator(
        camera=MockCameraDriver(),
        detector=MockDetector(),
        pose_estimator=MockPoseEstimator(),
        tracker=ByteTracker(high_score_thresh=0.4, match_thresh=0.3),
        event_bus=bus,
        station_id="BAS-TEST-BENCH",
    )


@pytest.fixture
def mock_app_settings() -> OrionSettings:
    sample_video = Path("assets/sample_replay.mp4")
    return OrionSettings(
        ORION_ENV="testing",
        ORION_STATION_ID="BAS-TEST-BENCH",
        api=ApiSettings(secret_key="test-insecure-secret-key-32-characters-minimum"),
        camera=CameraSettings(
            source=str(sample_video) if sample_video.exists() else "0",
            fps=30,
            width=640,
            height=480,
        ),
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_1_fastapi_lifespan_starts_perception_pipeline(
    mock_app_settings: OrionSettings,
) -> None:
    """TEST 1: FastAPI lifespan starts the perception pipeline."""
    app = create_app(settings=mock_app_settings)

    async with app.router.lifespan_context(app):
        coordinator = get_coordinator()
        assert coordinator is not None
        assert coordinator.is_running is True
        assert coordinator.camera.is_active is True


@pytest.mark.asyncio
@pytest.mark.integration
async def test_2_fastapi_shutdown_stops_perception_pipeline_cleanly(
    mock_app_settings: OrionSettings,
) -> None:
    """TEST 2: FastAPI shutdown stops the perception pipeline cleanly without leaked tasks."""
    app = create_app(settings=mock_app_settings)
    captured_coordinator: PerceptionPipelineCoordinator | None = None

    running_during_lifespan: bool = False
    async with app.router.lifespan_context(app):
        captured_coordinator = get_coordinator()
        running_during_lifespan = bool(captured_coordinator.is_running)

    assert running_during_lifespan is True
    assert captured_coordinator is not None
    stopped_state: bool = captured_coordinator.is_running
    assert stopped_state is False
    assert getattr(captured_coordinator.camera, "is_active", None) is False
    # Verify DI instance reset
    with pytest.raises(RuntimeError, match="PerceptionPipelineCoordinator not initialized"):
        get_coordinator()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_3_structured_observation_enters_event_bus() -> None:
    """TEST 3: A generated Structured Observation enters the EventBus and reaches subscribers."""
    bus = InMemoryEventBus()
    coordinator = _build_test_coordinator(bus)
    await coordinator.camera.initialize()

    captured_observations: list[ObservationCaptured] = []

    async def on_obs(evt: ObservationCaptured) -> None:
        captured_observations.append(evt)

    bus.subscribe(ObservationCaptured, on_obs)

    # Process single frame
    obs = await coordinator.process_single_frame()
    await coordinator.camera.shutdown()

    assert len(captured_observations) == 1
    event = captured_observations[0]
    assert isinstance(event, ObservationCaptured)
    assert event.event_type == "ObservationCaptured"
    assert event.station_id == "BAS-TEST-BENCH"
    assert event.observation.frame_index == obs.frame_index
    assert len(event.observation.detections) == 1
    assert len(event.observation.poses) == 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_4_websocket_forwarding_path_receives_observation() -> None:
    """TEST 4: The WebSocket forwarding path receives the observation and formats TELEMETRY_FRAME."""
    manager = WebSocketConnectionManager(queue_maxsize=16)

    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_json = AsyncMock()

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=16)
    manager._client_queues[mock_ws] = queue

    bus = InMemoryEventBus()
    coordinator = _build_test_coordinator(bus)
    await coordinator.camera.initialize()

    # Wire forwarder as done in app lifespan
    async def _forwarder(event: BaseEvent) -> None:
        if isinstance(event, ObservationCaptured):
            await manager.broadcast_observation(event.observation)

    bus.subscribe(BaseEvent, _forwarder)

    # Trigger single frame pass
    await coordinator.process_single_frame()
    await coordinator.camera.shutdown()

    assert not queue.empty()
    item = queue.get_nowait()
    assert item["type"] == "TELEMETRY_FRAME"
    assert item["station_id"] == "BAS-TEST-BENCH"
    assert item["frame_index"] == 1
    assert len(item["detections"]) == 1
    assert len(item["poses"]) == 1
    assert "metrics" in item
    assert item["pipeline_status"] == "NOMINAL"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_5_frontend_telemetry_json_serializable() -> None:
    """TEST 5: Frontend-facing telemetry JSON is serializable and contains expected fields."""
    bus = InMemoryEventBus()
    coordinator = _build_test_coordinator(bus)
    await coordinator.camera.initialize()

    obs = await coordinator.process_single_frame()
    await coordinator.camera.shutdown()

    # Emulate ws_manager.broadcast_observation payload formatting
    payload = {
        "type": "TELEMETRY_FRAME",
        "station_id": obs.station_id,
        "frame_index": obs.frame_index,
        "timestamp_utc": obs.timestamp_utc.isoformat(),
        "source_id": obs.source_id,
        "width": obs.width,
        "height": obs.height,
        "detections": [d.model_dump() for d in obs.detections],
        "poses": [p.model_dump() for p in obs.poses],
        "tracks": [t.model_dump() for t in obs.tracks],
        "activities": [a.model_dump() for a in obs.activities],
        "top_activity": obs.top_activity.activity_name if obs.top_activity else None,
        "hands": [h.model_dump(mode="json") for h in obs.hand_observations],
        "objects": [o.model_dump(mode="json") for o in obs.object_observations],
        "interactions": [i.model_dump(mode="json") for i in obs.interaction_observations],
        "multimodal_evidence": (
            obs.multimodal_evidence.model_dump(mode="json") if obs.multimodal_evidence else None
        ),
        "metrics": obs.metrics.model_dump(),
        "pipeline_status": obs.pipeline_status,
    }

    # Verify standard JSON serialization succeeds
    json_str = json.dumps(payload)
    assert json_str is not None

    parsed = json.loads(json_str)
    assert parsed["type"] == "TELEMETRY_FRAME"
    assert parsed["station_id"] == "BAS-TEST-BENCH"
    assert parsed["frame_index"] == 1
    assert "detections" in parsed
    assert "poses" in parsed
    assert "tracks" in parsed
    assert "hands" in parsed
    assert "objects" in parsed
    assert "interactions" in parsed
    assert "metrics" in parsed
    assert "pipeline_status" in parsed


@pytest.mark.asyncio
@pytest.mark.integration
async def test_6_pipeline_failure_handled_without_unmanaged_tasks() -> None:
    """TEST 6: Pipeline failure is logged/handled without leaving unmanaged tasks."""
    bus = InMemoryEventBus()
    coordinator = _build_test_coordinator(bus)

    # Force camera.read_frame to raise a transient error
    coordinator.camera.read_frame = AsyncMock(
        side_effect=RuntimeError("Transient optical sensor glitch")
    )  # type: ignore[method-assign]
    await coordinator.camera.initialize()

    # Start loop
    await coordinator.start()
    initially_running: bool = coordinator.is_running
    assert initially_running is True
    loop_task = coordinator._loop_task
    assert loop_task is not None
    initial_done: bool = loop_task.done()
    assert initial_done is False

    # Let loop attempt processing and encounter handled exception
    await asyncio.sleep(0.15)

    # Stop coordinator cleanly
    await coordinator.stop()
    finally_running: bool = coordinator.is_running
    assert finally_running is False
    final_done: bool = loop_task.done()
    assert final_done is True


@pytest.mark.asyncio
@pytest.mark.integration
async def test_7_no_duplicate_subscribers_or_broadcasts(mock_app_settings: OrionSettings) -> None:
    """TEST 7: No duplicate subscribers or duplicate WebSocket broadcasts are created."""
    app = create_app(settings=mock_app_settings)

    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_json = AsyncMock()

    client_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=32)
    ws_manager._client_queues[mock_ws] = client_queue

    try:
        async with app.router.lifespan_context(app):
            bus = get_event_bus()
            assert isinstance(bus, InMemoryEventBus)
            coordinator = get_coordinator()

            # Verify subscriber counts for BaseEvent on the bus
            subscribers = bus._global_handlers
            # Only one _ws_event_forwarder should be registered for BaseEvent
            assert len(subscribers) == 1

            # Capture an observation while coordinator is active, or construct deterministic test observation
            dummy_obs = coordinator.latest_observation or StructuredObservation(
                station_id="BAS-TEST-BENCH",
                frame_index=9999,
                timestamp_utc=datetime.now(UTC),
                source_id="test_cam",
                width=640,
                height=480,
            )

            # Stop the continuous background loop to test discrete event deduplication deterministically
            await coordinator.stop()

            # Drain queue of any remaining frames
            while not client_queue.empty():
                client_queue.get_nowait()

            # Now manually publish an ObservationCaptured event
            dummy_obs.frame_index = 9999
            evt = ObservationCaptured(
                station_id="BAS-TEST-BENCH",
                observation=dummy_obs,
            )
            await bus.publish(evt)

            # Wait briefly for fanout
            await asyncio.sleep(0.05)

            # Collect all frames delivered for this single observation
            delivered_frames: list[dict[str, Any]] = []
            while not client_queue.empty():
                msg = client_queue.get_nowait()
                if msg.get("type") == "TELEMETRY_FRAME" and msg.get("frame_index") == 9999:
                    delivered_frames.append(msg)

            # Exactly one TELEMETRY_FRAME must be broadcast for the single observation
            assert len(delivered_frames) == 1

            # Now publish intermediate partial telemetry events (FrameCaptured, DetectionCompleted, PoseCompleted)
            await bus.publish(
                FrameCaptured(
                    station_id="BAS-TEST-BENCH",
                    camera_id="cam_01",
                    frame_index=999,
                    width=640,
                    height=480,
                    pixel_format="BGR8",
                    timestamp_sensor_ns=12345,
                    latency_ms=1.0,
                )
            )
            await bus.publish(
                DetectionCompleted(
                    station_id="BAS-TEST-BENCH",
                    frame_index=999,
                    detection_count=0,
                    classes_detected=[],
                    inference_time_ms=2.0,
                )
            )
            await bus.publish(
                PoseCompleted(
                    station_id="BAS-TEST-BENCH",
                    frame_index=999,
                    person_count=0,
                    topology="coco_17",
                    inference_time_ms=2.0,
                )
            )

            await asyncio.sleep(0.05)

            # None of these raw intermediate partial events should have broadcast over WebSocket
            intermediate_broadcasts: list[dict[str, Any]] = []
            while not client_queue.empty():
                intermediate_broadcasts.append(client_queue.get_nowait())

            assert len(intermediate_broadcasts) == 0, (
                f"Expected 0 intermediate broadcasts, got {intermediate_broadcasts}"
            )
    finally:
        ws_manager.disconnect(mock_ws)
