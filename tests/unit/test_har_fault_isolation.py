"""Unit tests verifying fault-isolated graceful degradation of HAR stage in Perception Coordinator."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from orion.core.in_memory_event_bus import InMemoryEventBus
from orion_ai.camera.schemas import FrameContract, Resolution
from orion_ai.detection.schemas import BoundingBox2D, DetectionResult, DetectionTarget
from orion_ai.pose.schemas import HumanPose, Keypoint2D, PoseEstimationResult
from orion_ai.runtime.coordinator import PerceptionPipelineCoordinator
from orion_ai.tracking.schemas import TrackedObject, TrackingResult, TrackState


@pytest.mark.asyncio
async def test_coordinator_fault_isolation_when_har_throws() -> None:
    # 1. Setup mock camera
    mock_camera = AsyncMock()
    contract = FrameContract(
        camera_id="CAM_TEST",
        frame_index=1,
        timestamp_utc=datetime.now(UTC),
        timestamp_sensor_ns=1000,
        resolution=Resolution(width=640, height=480),
        pixel_format="RGB8",
    )
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_camera.read_frame.return_value = (contract, frame)
    mock_camera.dropped_frames = 0

    # 2. Setup mock detector
    mock_detector = AsyncMock()
    mock_detector.detect.return_value = DetectionResult(
        frame_index=1,
        timestamp_sensor_ns=1000,
        detections=[
            DetectionTarget(
                class_id=0,
                class_name="person",
                confidence=0.9,
                box=BoundingBox2D(x_min=10, y_min=10, x_max=100, y_max=200),
            )
        ],
        inference_latency_ms=10.0,
    )

    # 3. Setup mock tracker
    mock_tracker = MagicMock()
    mock_tracker.update.return_value = TrackingResult(
        frame_index=1,
        active_tracks=[
            TrackedObject(
                track_id=1,
                class_id=0,
                class_name="person",
                box=BoundingBox2D(x_min=10, y_min=10, x_max=100, y_max=200),
                confidence=0.9,
                state=TrackState.TRACKED,
                age_frames=1,
            )
        ],
    )

    # 4. Setup mock pose estimator
    mock_pose = AsyncMock()
    mock_pose.estimate.return_value = PoseEstimationResult(
        frame_index=1,
        poses=[
            HumanPose(
                person_id=1,
                bbox=BoundingBox2D(x_min=10, y_min=10, x_max=100, y_max=200, confidence=0.9),
                keypoints_2d=[
                    Keypoint2D(id=i, name=f"kp_{i}", x=50.0, y=100.0, score=0.9)
                    for i in range(17)
                ],
                overall_confidence=0.9,
            )
        ],
        inference_time_ms=12.0,
    )

    # 5. Faulty HAR Runtime that raises an unhandled Exception
    mock_har = AsyncMock()
    mock_har.process_frame_poses.side_effect = RuntimeError("Fatal GPU/Memory corruption simulation")

    event_bus = InMemoryEventBus()

    coordinator = PerceptionPipelineCoordinator(
        camera=mock_camera,
        detector=mock_detector,
        pose_estimator=mock_pose,
        tracker=mock_tracker,
        event_bus=event_bus,
        har_runtime=mock_har,
    )

    # Execute frame: must not raise, perception must survive!
    observation = await coordinator.process_single_frame()

    assert observation is not None
    assert observation.frame_index == 1
    # Optical perception was completely preserved
    assert len(observation.detections) == 1
    assert len(observation.poses) == 1
    assert len(observation.tracks) == 1
    # HAR was gracefully degraded
    assert observation.activities == []
    assert observation.top_activity is None
    assert observation.metrics.har_latency_ms >= 0.0
    assert observation.pipeline_status == "NOMINAL"
