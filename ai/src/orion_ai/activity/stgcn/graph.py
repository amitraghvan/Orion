"""COCO 17-keypoint skeleton graph representation and spatial partition matrices for ST-GCN."""

from typing import Any

import numpy as np
import torch

NUM_JOINTS: int = 17

# COCO-17 anatomical joints
COCO_JOINT_NAMES = [
    "nose",  # 0
    "left_eye",  # 1
    "right_eye",  # 2
    "left_ear",  # 3
    "right_ear",  # 4
    "left_shoulder",  # 5
    "right_shoulder",  # 6
    "left_elbow",  # 7
    "right_elbow",  # 8
    "left_wrist",  # 9
    "right_wrist",  # 10
    "left_hip",  # 11
    "right_hip",  # 12
    "left_knee",  # 13
    "right_knee",  # 14
    "left_ankle",  # 15
    "right_ankle",  # 16
]

# Anatomical bone edges (undirected)
COCO_BONES = [
    (0, 1),
    (0, 2),
    (1, 3),
    (2, 4),  # head
    (5, 6),  # shoulders
    (5, 7),
    (7, 9),  # left arm
    (6, 8),
    (8, 10),  # right arm
    (5, 11),
    (6, 12),  # torso sides
    (11, 12),  # hips
    (11, 13),
    (13, 15),  # left leg
    (12, 14),
    (14, 16),  # right leg
]

# Approximate topological distance from gravity center (mid-hip / trunk root)
# Joints with lower distance rank are "inward" (closer to torso center)
JOINT_DISTANCE_TO_CENTER = {
    11: 0,
    12: 0,  # hips (center)
    5: 1,
    6: 1,  # shoulders
    0: 2,  # nose / neck
    7: 2,
    8: 2,  # elbows
    13: 2,
    14: 2,  # knees
    1: 3,
    2: 3,  # eyes
    9: 3,
    10: 3,  # wrists
    15: 3,
    16: 3,  # ankles
    3: 4,
    4: 4,  # ears
}


class SkeletonGraph:
    """COCO 17-keypoint graph generating normalized 3-partition adjacency matrices."""

    def __init__(self, num_nodes: int = NUM_JOINTS) -> None:
        self.num_nodes = num_nodes
        self.num_partitions = 3
        self.A = self._build_spatial_adjacency_matrix()

    def _build_spatial_adjacency_matrix(self) -> np.ndarray[Any, Any]:
        """Construct normalized 3-partition adjacency matrix (shape: 3, 17, 17).

        Partitions:
        - 0: Root node self-connection (identity)
        - 1: Centripetal / Inward connections (neighbor is closer to center)
        - 2: Centrifugal / Outward connections (neighbor is farther from center)
        """
        adj_self = np.eye(self.num_nodes, dtype=np.float32)
        adj_inward = np.zeros((self.num_nodes, self.num_nodes), dtype=np.float32)
        adj_outward = np.zeros((self.num_nodes, self.num_nodes), dtype=np.float32)

        for u, v in COCO_BONES:
            dist_u = JOINT_DISTANCE_TO_CENTER.get(u, 2)
            dist_v = JOINT_DISTANCE_TO_CENTER.get(v, 2)

            if dist_u < dist_v:
                # u is closer to center: v -> u is inward; u -> v is outward
                adj_inward[v, u] = 1.0
                adj_outward[u, v] = 1.0
            elif dist_u > dist_v:
                # v is closer to center: u -> v is inward; v -> u is outward
                adj_inward[u, v] = 1.0
                adj_outward[v, u] = 1.0
            else:
                # Equal distance: symmetric connection across both inward and outward
                adj_inward[u, v] = 1.0
                adj_inward[v, u] = 1.0

        # Degree normalize each partition: A_norm = D^{-1} * A
        matrices = [adj_self, adj_inward, adj_outward]
        norm_matrices = []

        for mat in matrices:
            row_sum = np.sum(mat, axis=1)
            row_sum[row_sum == 0] = 1.0
            inv_d = np.diag(1.0 / row_sum)
            norm_matrices.append(np.dot(inv_d, mat))

        return np.stack(norm_matrices, axis=0)  # shape: (3, 17, 17)

    def to_tensor(self) -> torch.Tensor:
        """Return adjacency matrix as float32 torch.Tensor."""
        return torch.from_numpy(self.A).float()
