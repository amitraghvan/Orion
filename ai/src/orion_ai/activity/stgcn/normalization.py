"""Canonical microgravity-motivated normalization pipeline for 17-keypoint skeleton sequences."""

import numpy as np
import torch

from orion_ai.activity.schemas import TemporalSkeletonPose

DEFAULT_EPSILON: float = 1e-4
LEFT_HIP_IDX: int = 11
RIGHT_HIP_IDX: int = 12
LEFT_SHOULDER_IDX: int = 5
RIGHT_SHOULDER_IDX: int = 6
NUM_JOINTS: int = 17


class MicrogravityNormalizer:
    """Canonical geometric transformation pipeline for microgravity skeleton normalization."""

    def __init__(self, epsilon: float = DEFAULT_EPSILON) -> None:
        self.epsilon = epsilon

    def normalize_sequence(
        self,
        sequence: list[TemporalSkeletonPose],
        width: int = 640,
        height: int = 480,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Convert a sequence of T skeletal poses into normalized ST-GCN input features.

        Returns:
            feature_tensor: torch.Tensor of shape (C=4, T, V=17) [x_norm, y_norm, v_x, v_y]
            confidence_tensor: torch.Tensor of shape (T, V=17) [joint_confidences]
        """
        T = len(sequence)
        if T == 0:
            return (
                torch.zeros((4, 0, NUM_JOINTS), dtype=torch.float32),
                torch.zeros((0, NUM_JOINTS), dtype=torch.float32),
            )

        max_dim = float(max(width, height))
        half_w = float(width) / 2.0
        half_h = float(height) / 2.0

        coords = np.zeros((T, NUM_JOINTS, 2), dtype=np.float32)
        confs = np.zeros((T, NUM_JOINTS), dtype=np.float32)

        for t_idx, pose in enumerate(sequence):
            for kp in pose.keypoints_2d:
                if 0 <= kp.id < NUM_JOINTS:
                    # Step 1: Canonical normalized image space [-0.5, 0.5]
                    canonical_x = (kp.x - half_w) / max_dim
                    canonical_y = (kp.y - half_h) / max_dim
                    coords[t_idx, kp.id, 0] = canonical_x
                    coords[t_idx, kp.id, 1] = canonical_y
                    confs[t_idx, kp.id] = kp.score

        # Step 2: Root centering at astronaut mid-hip
        norm_coords = np.zeros_like(coords)

        for t in range(T):
            left_hip = coords[t, LEFT_HIP_IDX]
            right_hip = coords[t, RIGHT_HIP_IDX]
            root = (left_hip + right_hip) / 2.0

            # Centering relative to root
            centered = coords[t] - root  # shape: (17, 2)

            # Step 3: Trunk scale normalization
            left_shoulder = coords[t, LEFT_SHOULDER_IDX]
            right_shoulder = coords[t, RIGHT_SHOULDER_IDX]
            mid_shoulder = (left_shoulder + right_shoulder) / 2.0
            trunk_dist = float(np.linalg.norm(mid_shoulder - root))
            s_safe = max(trunk_dist, self.epsilon)

            norm_coords[t] = centered / s_safe

        # Step 4: Motion velocity calculation (first-order backward difference)
        velocities = np.zeros_like(norm_coords)
        if T > 1:
            velocities[1:] = norm_coords[1:] - norm_coords[:-1]

        # Step 5: Pack into (C=4, T, V=17) -> [x_norm, y_norm, v_x, v_y]
        features = np.zeros((4, T, NUM_JOINTS), dtype=np.float32)
        features[0] = norm_coords[:, :, 0]
        features[1] = norm_coords[:, :, 1]
        features[2] = velocities[:, :, 0]
        features[3] = velocities[:, :, 1]

        return torch.from_numpy(features), torch.from_numpy(confs)
