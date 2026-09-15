"""Unit tests for ByteTracker multi-class protection and person track queries."""

import pytest

from orion_ai.detection.schemas import BoundingBox2D, DetectionResult, DetectionTarget
from orion_ai.tracking.byte_tracker import ByteTracker
from orion_ai.tracking.schemas import TrackState


def test_bytetrack_prevents_cross_class_track_hijacking() -> None:
    """Verify that an overlapping detection of a different class NEVER hijacks an existing track."""
    tracker = ByteTracker(high_score_thresh=0.4, match_thresh=0.3)

    # Frame 1: Person at box [100, 100, 200, 200]
    det_f1 = DetectionResult(
        frame_index=1,
        timestamp_sensor_ns=1000,
        detections=[
            DetectionTarget(
                class_id=0,
                class_name="person",
                confidence=0.9,
                box=BoundingBox2D(x_min=100.0, y_min=100.0, x_max=200.0, y_max=200.0),
            )
        ],
        inference_latency_ms=10.0,
    )
    res_f1 = tracker.update(det_f1)
    assert len(res_f1.active_tracks) == 1
    person_track_id = res_f1.active_tracks[0].track_id
    assert res_f1.active_tracks[0].class_id == 0

    # Frame 2: A bottle (class_id=39) appears at the EXACT SAME box [100, 100, 200, 200]
    det_f2 = DetectionResult(
        frame_index=2,
        timestamp_sensor_ns=2000,
        detections=[
            DetectionTarget(
                class_id=39,
                class_name="bottle",
                confidence=0.85,
                box=BoundingBox2D(x_min=100.0, y_min=100.0, x_max=200.0, y_max=200.0),
            )
        ],
        inference_latency_ms=10.0,
    )
    res_f2 = tracker.update(det_f2)

    # Bottle MUST receive a brand new track ID and NOT hijack person_track_id!
    bottle_track = next((t for t in res_f2.active_tracks if t.class_id == 39), None)
    assert bottle_track is not None
    assert bottle_track.track_id != person_track_id
    assert bottle_track.class_name == "bottle"

    # The original person track should be marked LOST, not transformed into a bottle
    assert person_track_id in tracker._tracks
    assert tracker._tracks[person_track_id].class_id == 0
    assert tracker._tracks[person_track_id].state == TrackState.LOST


def test_bytetrack_get_person_tracks_filter() -> None:
    """Verify that get_person_tracks returns only person tracklets."""
    tracker = ByteTracker(high_score_thresh=0.4, match_thresh=0.3)

    # Detections containing both a person and a piece of equipment
    detections = DetectionResult(
        frame_index=1,
        timestamp_sensor_ns=1000,
        detections=[
            DetectionTarget(
                class_id=0,
                class_name="person",
                confidence=0.92,
                box=BoundingBox2D(x_min=50.0, y_min=50.0, x_max=150.0, y_max=250.0),
            ),
            DetectionTarget(
                class_id=56,
                class_name="chair",
                confidence=0.88,
                box=BoundingBox2D(x_min=300.0, y_min=200.0, x_max=400.0, y_max=350.0),
            ),
        ],
        inference_latency_ms=12.0,
    )
    tracker.update(detections)

    person_tracks = tracker.get_person_tracks(person_class_id=0)
    assert len(person_tracks) == 1
    assert person_tracks[0].class_id == 0
    assert person_tracks[0].class_name == "person"
