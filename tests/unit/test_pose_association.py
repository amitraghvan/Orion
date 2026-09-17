"""Unit tests for Hungarian bipartite pose-to-track identity association."""

from orion_ai.detection.schemas import BoundingBox2D
from orion_ai.pose.schemas import HumanPose, Keypoint2D
from orion_ai.runtime.coordinator import _associate_poses_with_tracks, _compute_bbox_iou
from orion_ai.tracking.schemas import TrackedObject, TrackState


def _dummy_pose(bbox: BoundingBox2D, person_id: int = 1) -> HumanPose:
    return HumanPose(
        person_id=person_id,
        bbox=bbox,
        topology="coco_17",
        keypoints_2d=[
            Keypoint2D(id=0, name="nose", x=bbox.x_min + 10, y=bbox.y_min + 10, score=0.9)
        ],
        overall_confidence=0.85,
    )


def _dummy_track(track_id: int, box: BoundingBox2D, class_id: int = 0) -> TrackedObject:
    return TrackedObject(
        track_id=track_id,
        class_id=class_id,
        class_name="person" if class_id == 0 else "equipment",
        box=box,
        velocity_px_per_sec=(0.0, 0.0),
        confidence=0.9,
        state=TrackState.TRACKED,
        age_frames=5,
    )


def test_compute_bbox_iou() -> None:
    """Verify IoU calculation between matching, overlapping, and disjoint boxes."""
    b1 = BoundingBox2D(x_min=0.0, y_min=0.0, x_max=100.0, y_max=100.0)
    b2 = BoundingBox2D(x_min=0.0, y_min=0.0, x_max=100.0, y_max=100.0)
    assert _compute_bbox_iou(b1, b2) == 1.0

    b3 = BoundingBox2D(x_min=50.0, y_min=0.0, x_max=150.0, y_max=100.0)
    iou_half = _compute_bbox_iou(b1, b3)
    assert 0.3 < iou_half < 0.4  # intersection=5000, union=15000 -> 0.333

    b4 = BoundingBox2D(x_min=200.0, y_min=200.0, x_max=300.0, y_max=300.0)
    assert _compute_bbox_iou(b1, b4) == 0.0


def test_hungarian_pose_association_matches_tracks_by_iou() -> None:
    """Verify that Hungarian matching associates poses with correct track IDs based on spatial overlap."""
    # Person A is on the left; Person B is on the right
    track_left = _dummy_track(
        track_id=101, box=BoundingBox2D(x_min=50.0, y_min=50.0, x_max=150.0, y_max=300.0)
    )
    track_right = _dummy_track(
        track_id=202, box=BoundingBox2D(x_min=400.0, y_min=50.0, x_max=500.0, y_max=300.0)
    )

    # Pose 1 corresponds to right person; Pose 2 corresponds to left person (inverted detection order)
    pose_right = _dummy_pose(
        bbox=BoundingBox2D(x_min=395.0, y_min=55.0, x_max=495.0, y_max=295.0), person_id=1
    )
    pose_left = _dummy_pose(
        bbox=BoundingBox2D(x_min=55.0, y_min=45.0, x_max=145.0, y_max=305.0), person_id=2
    )

    poses = [pose_right, pose_left]
    tracks = [track_left, track_right]

    _associate_poses_with_tracks(poses, tracks, min_iou_thresh=0.2)

    # pose_right must be matched to track_right (202) despite being first in poses array!
    assert pose_right.person_id == 202
    # pose_left must be matched to track_left (101)
    assert pose_left.person_id == 101


def test_hungarian_pose_association_fallback_when_no_tracks() -> None:
    """Verify safe fallback when tracks list is empty."""
    pose = _dummy_pose(
        bbox=BoundingBox2D(x_min=10.0, y_min=10.0, x_max=50.0, y_max=100.0), person_id=99
    )
    poses = [pose]

    _associate_poses_with_tracks(poses, [], min_iou_thresh=0.2)
    assert pose.person_id == 1
