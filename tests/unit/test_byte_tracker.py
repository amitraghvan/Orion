"""Unit tests for ByteTracker multi-object tracking and ID persistence."""

import time

import pytest

from orion_ai.detection.schemas import BoundingBox2D, DetectionResult, DetectionTarget
from orion_ai.tracking.byte_tracker import ByteTracker
from orion_ai.tracking.schemas import TrackingResult, TrackState


@pytest.mark.unit
def test_byte_tracker_creation_and_persistence() -> None:
    """Verify tracker assigns track IDs and preserves identity across frames."""
    tracker = ByteTracker(high_score_thresh=0.5, match_thresh=0.3)

    # Frame 1: Single detection
    det1 = DetectionTarget(
        class_id=0,
        class_name="person",
        confidence=0.9,
        box=BoundingBox2D(x_min=100.0, y_min=100.0, x_max=200.0, y_max=300.0),
    )
    res1 = DetectionResult(
        frame_index=1,
        timestamp_sensor_ns=time.time_ns(),
        detections=[det1],
        inference_latency_ms=10.0,
    )

    track_res1 = tracker.update(res1)
    assert isinstance(track_res1, TrackingResult)
    assert len(track_res1.active_tracks) == 1
    t1 = track_res1.active_tracks[0]
    assert t1.track_id == 1
    assert t1.class_name == "person"
    assert t1.state in (TrackState.NEW, TrackState.TRACKED)

    # Frame 2: Slightly shifted detection (overlapping)
    det2 = DetectionTarget(
        class_id=0,
        class_name="person",
        confidence=0.88,
        box=BoundingBox2D(x_min=105.0, y_min=102.0, x_max=205.0, y_max=302.0),
    )
    res2 = DetectionResult(
        frame_index=2,
        timestamp_sensor_ns=time.time_ns(),
        detections=[det2],
        inference_latency_ms=10.0,
    )

    track_res2 = tracker.update(res2)
    assert len(track_res2.active_tracks) == 1
    t2 = track_res2.active_tracks[0]
    # Verify ID persistence!
    assert t2.track_id == 1
    assert t2.state == TrackState.TRACKED

    # Reset
    tracker.reset()
    assert len(tracker._tracks) == 0
