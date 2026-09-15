"""Unit tests verifying multi-person isolation and track loss handling in TemporalHARRuntime."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from orion_ai.activity.configs import ActivityConfig
from orion_ai.activity.runtime import TemporalHARRuntime
from orion_ai.activity.schemas import ActivityPhase
from orion_ai.detection.schemas import BoundingBox2D
from orion_ai.pose.schemas import HumanPose, Keypoint2D


@pytest.mark.asyncio
async def test_har_multi_person_isolation_and_track_loss() -> None:
    weights_path = Path("models/weights/stgcn_har_v1.pt")
    if not weights_path.exists():
        pytest.skip("ST-GCN weights not found.")

    config = ActivityConfig(
        model_id="stgcn_har_v1",
        window_size_frames=8,  # small window for test speed
        stride_frames=2,
        confidence_threshold=0.3,
    )
    runtime = TemporalHARRuntime(
        config=config,
        model_path=str(weights_path),
        device="cpu",
    )
    await runtime.initialize()

    # Create 2 distinct subjects
    bbox1 = BoundingBox2D(x_min=10, y_min=10, x_max=100, y_max=200, confidence=0.9)
    bbox2 = BoundingBox2D(x_min=300, y_min=10, x_max=400, y_max=200, confidence=0.9)

    # Feed 10 frames with both persons
    for f_idx in range(10):
        pose1 = HumanPose(
            person_id=1,
            bbox=bbox1,
            keypoints_2d=[
                Keypoint2D(id=i, name=f"kp_{i}", x=50.0 + i, y=100.0 + i * 2, score=0.9)
                for i in range(17)
            ],
            overall_confidence=0.9,
        )
        pose2 = HumanPose(
            person_id=2,
            bbox=bbox2,
            keypoints_2d=[
                Keypoint2D(id=i, name=f"kp_{i}", x=350.0 + i, y=100.0 + i * 2, score=0.9)
                for i in range(17)
            ],
            overall_confidence=0.9,
        )

        results, events = await runtime.process_frame_poses(
            frame_index=f_idx,
            poses=[pose1, pose2],
            fps=30,
        )

    # Check results: Both persons should have recognized activities
    track_ids = {r.track_id for r in results}
    assert 1 in track_ids
    assert 2 in track_ids

    # Check buffer isolation: Person 1 buffer must have 8 frames, Person 2 buffer must have 8 frames
    assert len(runtime.buffer._buffers[1]) == 8
    assert len(runtime.buffer._buffers[2]) == 8

    # Simulate Person 2 disappearing (stale eviction threshold is 30 frames)
    # Feed frames 10 to 45 with only Person 1
    events_collected = []
    for f_idx in range(10, 45):
        pose1 = HumanPose(
            person_id=1,
            bbox=bbox1,
            keypoints_2d=[
                Keypoint2D(id=i, name=f"kp_{i}", x=50.0 + i, y=100.0 + i * 2, score=0.9)
                for i in range(17)
            ],
            overall_confidence=0.9,
        )
        results, events = await runtime.process_frame_poses(
            frame_index=f_idx,
            poses=[pose1],
            fps=30,
        )
        events_collected.extend(events)

    # Person 2 should now be evicted from active buffer
    assert 2 not in runtime.buffer._buffers
    assert 1 in runtime.buffer._buffers

    # Check that END event was emitted for Person 2
    end_events_p2 = [
        e for e in events_collected
        if e.track_id == 2 and e.phase == ActivityPhase.END.value
    ]
    assert len(end_events_p2) >= 1
    assert end_events_p2[0].evidence_metadata.get("evicted") is True

    await runtime.shutdown()
