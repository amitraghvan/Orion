"""Unit tests for TemporalFeatureBuffer multi-person isolation, stride triggers, and degradation."""

from orion_ai.activity.buffer import TemporalFeatureBuffer
from orion_ai.activity.schemas import KeypointState
from orion_ai.detection.schemas import BoundingBox2D
from orion_ai.pose.schemas import HumanPose, Keypoint2D


def _dummy_pose(track_id: int, nose_conf: float = 0.9) -> HumanPose:
    kps = [
        Keypoint2D(id=0, name="nose", x=100.0, y=100.0, score=nose_conf),
        Keypoint2D(id=1, name="left_eye", x=105.0, y=95.0, score=0.85),
    ]
    # Fill remaining 15 joints with nominal score
    for idx in range(2, 17):
        kps.append(Keypoint2D(id=idx, name=f"joint_{idx}", x=120.0, y=150.0, score=0.8))

    return HumanPose(
        person_id=track_id,
        bbox=BoundingBox2D(x_min=80.0, y_min=80.0, x_max=160.0, y_max=240.0),
        topology="coco_17",
        keypoints_2d=kps,
        overall_confidence=0.85,
    )


def test_buffer_per_track_isolation() -> None:
    """Verify that multiple tracks maintain independent queues without cross-talk."""
    buf = TemporalFeatureBuffer(window_size=16, stride_frames=4)

    # Push 10 frames for track 101, 5 frames for track 202
    for f in range(1, 11):
        buf.push_pose(_dummy_pose(101), frame_index=f)
    for f in range(1, 6):
        buf.push_pose(_dummy_pose(202), frame_index=f)

    assert len(buf.peek_window(101)) == 10
    assert len(buf.peek_window(202)) == 5
    assert not buf.is_window_ready(101)
    assert not buf.is_window_ready(202)


def test_buffer_stride_trigger_and_bounded_capacity() -> None:
    """Verify window ready, stride trigger, and capacity bounding at window_size."""
    buf = TemporalFeatureBuffer(window_size=10, stride_frames=3)

    # Push 10 frames
    for f in range(1, 11):
        buf.push_pose(_dummy_pose(101), frame_index=f)

    assert buf.is_window_ready(101)
    assert buf.should_classify(101)

    # Pull window
    window = buf.get_window(101)
    assert len(window) == 10
    # Immediately after pull, stride is reset
    assert not buf.should_classify(101)

    # Push 2 more frames (stride is 3) -> should not classify yet
    buf.push_pose(_dummy_pose(101), frame_index=11)
    buf.push_pose(_dummy_pose(101), frame_index=12)
    assert not buf.should_classify(101)

    # 3rd frame -> stride interval met!
    buf.push_pose(_dummy_pose(101), frame_index=13)
    assert buf.should_classify(101)

    # Total buffer length should still be exactly 10 (bounded)
    assert len(buf.peek_window(101)) == 10


def test_buffer_missing_keypoint_degradation() -> None:
    """Verify keypoint state transitions: OBSERVED -> INTERPOLATED -> HELD -> INVALID."""
    buf = TemporalFeatureBuffer(window_size=10, stride_frames=2)

    # Frame 1: cleanly observed (conf=0.90)
    buf.push_pose(_dummy_pose(101, nose_conf=0.90), frame_index=1)
    p1 = buf.peek_window(101)[-1]
    assert p1.keypoints_2d[0].state == KeypointState.OBSERVED
    assert p1.keypoints_2d[0].score == 0.90

    # Frame 2: missing joint (conf=0.05) -> INTERPOLATED (decayed)
    buf.push_pose(_dummy_pose(101, nose_conf=0.05), frame_index=2)
    p2 = buf.peek_window(101)[-1]
    assert p2.keypoints_2d[0].state == KeypointState.INTERPOLATED
    assert p2.keypoints_2d[0].score < 0.90

    # Frame 3: missing joint again -> INTERPOLATED (2nd frame)
    buf.push_pose(_dummy_pose(101, nose_conf=0.05), frame_index=3)
    p3 = buf.peek_window(101)[-1]
    assert p3.keypoints_2d[0].state == KeypointState.INTERPOLATED

    # Frame 4: missing 3rd consecutive frame -> HELD
    buf.push_pose(_dummy_pose(101, nose_conf=0.05), frame_index=4)
    p4 = buf.peek_window(101)[-1]
    assert p4.keypoints_2d[0].state == KeypointState.HELD
    assert p4.keypoints_2d[0].score == 0.20

    # Frame 5: missing 4th consecutive frame -> INVALID
    buf.push_pose(_dummy_pose(101, nose_conf=0.05), frame_index=5)
    p5 = buf.peek_window(101)[-1]
    assert p5.keypoints_2d[0].state == KeypointState.INVALID
    assert p5.keypoints_2d[0].score == 0.0


def test_buffer_stale_track_eviction() -> None:
    """Verify that vanished tracks are evicted once timeout threshold is exceeded."""
    buf = TemporalFeatureBuffer(window_size=10, stale_timeout_frames=15)

    # Track 101 seen up to frame 10
    for f in range(1, 11):
        buf.push_pose(_dummy_pose(101), frame_index=f)

    # Track 202 seen up to frame 20
    for f in range(11, 21):
        buf.push_pose(_dummy_pose(202), frame_index=f)

    assert 101 in buf.get_active_tracks()
    assert 202 in buf.get_active_tracks()

    # At frame 22: (22 - 10) = 12 <= 15 -> not evicted yet
    evicted = buf.evict_stale_tracks(current_frame_index=22)
    assert len(evicted) == 0

    # At frame 26: (26 - 10) = 16 > 15 -> track 101 evicted!
    evicted = buf.evict_stale_tracks(current_frame_index=26)
    assert evicted == [101]
    assert 101 not in buf.get_active_tracks()
    assert 202 in buf.get_active_tracks()
