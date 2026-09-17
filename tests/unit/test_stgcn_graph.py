"""Unit tests for SkeletonGraph topology and MicrogravityNormalizer robustness."""

import numpy as np
import torch

from orion_ai.activity.schemas import KeypointState, TemporalKeypoint, TemporalSkeletonPose
from orion_ai.activity.stgcn.graph import SkeletonGraph
from orion_ai.activity.stgcn.normalization import MicrogravityNormalizer
from orion_ai.detection.schemas import BoundingBox2D


def _create_synthetic_pose(
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    scale: float = 1.0,
    rotation_deg: float = 0.0,
    frame_index: int = 1,
) -> TemporalSkeletonPose:
    # Base canonical human coordinates (17 keypoints)
    base_coords = {
        0: (320.0, 100.0),  # nose
        1: (315.0, 95.0),  # left_eye
        2: (325.0, 95.0),  # right_eye
        3: (310.0, 100.0),  # left_ear
        4: (330.0, 100.0),  # right_ear
        5: (280.0, 150.0),  # left_shoulder
        6: (360.0, 150.0),  # right_shoulder
        7: (260.0, 200.0),  # left_elbow
        8: (380.0, 200.0),  # right_elbow
        9: (250.0, 250.0),  # left_wrist
        10: (390.0, 250.0),  # right_wrist
        11: (290.0, 270.0),  # left_hip
        12: (350.0, 270.0),  # right_hip
        13: (285.0, 350.0),  # left_knee
        14: (355.0, 350.0),  # right_knee
        15: (280.0, 430.0),  # left_ankle
        16: (360.0, 430.0),  # right_ankle
    }

    rad = np.radians(rotation_deg)
    cos_r = np.cos(rad)
    sin_r = np.sin(rad)
    center = (320.0, 270.0)  # rotation around mid-hip

    kps = []
    for jid, (x, y) in base_coords.items():
        # Rotate around center
        dx = (x - center[0]) * scale
        dy = (y - center[1]) * scale
        rx = center[0] + dx * cos_r - dy * sin_r + offset_x
        ry = center[1] + dx * sin_r + dy * cos_r + offset_y

        kps.append(
            TemporalKeypoint(
                id=jid,
                name=f"joint_{jid}",
                x=float(rx),
                y=float(ry),
                score=0.9,
                state=KeypointState.OBSERVED,
            )
        )

    return TemporalSkeletonPose(
        frame_index=frame_index,
        track_id=1,
        bbox=BoundingBox2D(x_min=200.0, y_min=80.0, x_max=440.0, y_max=450.0),
        keypoints_2d=kps,
        overall_confidence=0.9,
    )


def test_skeleton_graph_topology() -> None:
    """Verify COCO 17-joint graph adjacency matrix structure and 3-partition normalization."""
    graph = SkeletonGraph()
    A = graph.to_tensor()
    assert A.shape == (3, 17, 17)

    # Partition 0 (self loops) should be identity matrix
    assert torch.allclose(A[0], torch.eye(17))

    # All partition weights must be non-negative
    assert (A >= 0.0).all()


def test_microgravity_translation_invariance() -> None:
    """Verify that shifting the astronaut across camera frame produces identical normalized coordinates."""
    normalizer = MicrogravityNormalizer()

    # Sequence A: at nominal center
    seq_a = [_create_synthetic_pose(offset_x=0.0, offset_y=0.0, frame_index=i) for i in range(5)]
    feat_a, _ = normalizer.normalize_sequence(seq_a)

    # Sequence B: translated by +150px X, -80px Y
    seq_b = [
        _create_synthetic_pose(offset_x=150.0, offset_y=-80.0, frame_index=i) for i in range(5)
    ]
    feat_b, _ = normalizer.normalize_sequence(seq_b)

    # Coordinates and velocities must match within float precision
    assert torch.allclose(feat_a, feat_b, atol=1e-5)


def test_microgravity_scale_invariance() -> None:
    """Verify that scaling the astronaut size produces identical trunk-normalized coordinates."""
    normalizer = MicrogravityNormalizer()

    # Sequence A: scale 1.0
    seq_a = [_create_synthetic_pose(scale=1.0, frame_index=i) for i in range(5)]
    feat_a, _ = normalizer.normalize_sequence(seq_a)

    # Sequence B: scale 1.5x (astronaut closer to camera)
    seq_b = [_create_synthetic_pose(scale=1.5, frame_index=i) for i in range(5)]
    feat_b, _ = normalizer.normalize_sequence(seq_b)

    # Root-centered and trunk-distance normalized coordinates must match
    assert torch.allclose(feat_a[:2], feat_b[:2], atol=1e-4)


def test_microgravity_rotation_perturbation_empirical_baseline() -> None:
    """Empirically measure coordinate perturbation under planar rotations (Microgravity baseline)."""
    normalizer = MicrogravityNormalizer()

    seq_orig = [_create_synthetic_pose(rotation_deg=0.0, frame_index=i) for i in range(5)]
    feat_orig, _ = normalizer.normalize_sequence(seq_orig)

    # Rotate 15 degrees
    seq_15 = [_create_synthetic_pose(rotation_deg=15.0, frame_index=i) for i in range(5)]
    feat_15, _ = normalizer.normalize_sequence(seq_15)

    # Compute cosine similarity / difference
    diff_15 = torch.norm(feat_orig[:2] - feat_15[:2]).item()
    # Rotation perturbation should be bounded and measurable
    assert 0.0 < diff_15 < 5.0
