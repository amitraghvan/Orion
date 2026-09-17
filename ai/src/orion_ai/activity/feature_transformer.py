"""Canonical feature transformation module for ST-GCN Temporal HAR.

Ensures strict parity between dataset generation (training) and real-time
inference pipelines. All inputs are mapped to the canonical 4-channel tensor:
  Channel 0: x_norm = x / frame_width      in [0.0, 1.0]
  Channel 1: y_norm = y / frame_height     in [0.0, 1.0]
  Channel 2: confidence = joint score      in [0.0, 1.0]
  Channel 3: interaction_proximity         in [0.0, 1.0]
"""

from __future__ import annotations

import math
from typing import Any
import numpy as np

# Canonical COCO-17 keypoint indices for interaction propagation
INTERACTION_JOINTS = (7, 8, 9, 10)  # Left/Right Elbows and Wrists


class CanonicalFeatureTransformer:
    """Standardizes raw 2D keypoints and interaction scores into canonical ST-GCN features."""

    def __init__(self, num_joints: int = 17, proximity_normalizer_fraction: float = 0.25) -> None:
        self.num_joints = num_joints
        self.proximity_normalizer_fraction = proximity_normalizer_fraction

    def transform_frame(
        self,
        keypoints: np.ndarray | None,
        frame_width: float,
        frame_height: float,
        interaction_score: float = 0.0,
    ) -> np.ndarray:
        """Transform single-frame 2D keypoints into canonical (4, num_joints) feature matrix.

        Args:
            keypoints: Array of shape (num_joints, 3) containing [x_pixel, y_pixel, confidence].
            frame_width: Actual frame width in pixels (> 0).
            frame_height: Actual frame height in pixels (> 0).
            interaction_score: Hand-apparatus interaction proximity in [0.0, 1.0].

        Returns:
            np.ndarray of shape (4, num_joints), dtype float32 with values in [0.0, 1.0].
        """
        w = max(1.0, float(frame_width))
        h = max(1.0, float(frame_height))
        clamped_interaction = float(np.clip(interaction_score, 0.0, 1.0))

        if keypoints is None or len(keypoints) < self.num_joints:
            # Fallback zero representation
            feat = np.zeros((4, self.num_joints), dtype=np.float32)
            for j in INTERACTION_JOINTS:
                feat[3, j] = clamped_interaction
            return feat

        kpts = np.asarray(keypoints, dtype=np.float32)
        assert kpts.shape >= (self.num_joints, 3), f"Keypoints shape must be at least ({self.num_joints}, 3), got {kpts.shape}"

        # Channel 0: Normalized X in [0.0, 1.0]
        x_norm = np.clip(kpts[: self.num_joints, 0] / w, 0.0, 1.0)

        # Channel 1: Normalized Y in [0.0, 1.0]
        y_norm = np.clip(kpts[: self.num_joints, 1] / h, 0.0, 1.0)

        # Channel 2: Detection confidence in [0.0, 1.0]
        conf = np.clip(kpts[: self.num_joints, 2], 0.0, 1.0)

        # Channel 3: Hand-object interaction signal on wrists and elbows
        interact = np.zeros(self.num_joints, dtype=np.float32)
        for j in INTERACTION_JOINTS:
            interact[j] = clamped_interaction

        # Stack into (4, num_joints)
        frame_feat = np.stack([x_norm, y_norm, conf, interact], axis=0).astype(np.float32)

        # Invariant checks
        assert frame_feat.shape == (4, self.num_joints), f"Unexpected shape {frame_feat.shape}"
        assert 0.0 <= np.min(frame_feat) and np.max(frame_feat) <= 1.0, (
            f"Feature values out of range [0.0, 1.0]: min={np.min(frame_feat)}, max={np.max(frame_feat)}"
        )
        return frame_feat

    def compute_proximity(
        self,
        wrist_x_norm: float,
        wrist_y_norm: float,
        boxes: list[tuple[int, int, int, int] | list[float]],
        frame_width: float,
        frame_height: float,
    ) -> float:
        """Compute normalized proximity [0.0, 1.0] between a normalized wrist coordinate and boxes.

        Box format: (x, y, w, h) or [x1, y1, x2, y2].
        """
        if not boxes or wrist_x_norm <= 0.0 or wrist_y_norm <= 0.0:
            return 0.0

        w = max(1.0, float(frame_width))
        h = max(1.0, float(frame_height))
        diag = math.hypot(w, h)
        threshold_px = max(1.0, diag * self.proximity_normalizer_fraction)

        px = wrist_x_norm * w
        py = wrist_y_norm * h

        min_dist = float("inf")
        for b in boxes:
            if len(b) >= 4:
                # Handle both (x, y, w, h) and [x1, y1, x2, y2]
                if b[2] > b[0] and b[3] > b[1] and (b[2] - b[0] > 10):
                    # xyxy format
                    cx = (b[0] + b[2]) * 0.5
                    cy = (b[1] + b[3]) * 0.5
                else:
                    # xywh format
                    cx = b[0] + b[2] * 0.5
                    cy = b[1] + b[3] * 0.5

                dist = math.hypot(px - cx, py - cy)
                if dist < min_dist:
                    min_dist = dist

        if min_dist == float("inf"):
            return 0.0

        norm_dist = min_dist / threshold_px
        return float(np.clip(1.0 - norm_dist, 0.0, 1.0))

    @staticmethod
    def validate_tensor(tensor: np.ndarray) -> None:
        """Validate an ST-GCN input tensor before inference.

        Supports:
          - (1, 4, T, V) or (B, 4, T, V)
          - (4, T, V)
        """
        assert isinstance(tensor, np.ndarray), "Tensor must be a numpy.ndarray"
        if tensor.ndim == 4:
            b, c, t, v = tensor.shape
            assert c == 4, f"Expected 4 channels, got {c}"
            assert t == 32, f"Expected 32 temporal frames, got {t}"
            assert v == 17, f"Expected 17 joints, got {v}"
        elif tensor.ndim == 3:
            c, t, v = tensor.shape
            assert c == 4, f"Expected 4 channels, got {c}"
            assert t == 32, f"Expected 32 temporal frames, got {t}"
            assert v == 17, f"Expected 17 joints, got {v}"
        else:
            raise AssertionError(f"Invalid tensor dimensions: {tensor.shape}")

        min_val = float(np.min(tensor))
        max_val = float(np.max(tensor))
        assert -0.01 <= min_val, f"Tensor contains negative values: {min_val}"
        assert max_val <= 1.01, f"Tensor exceeds normalized range [0.0, 1.0]: {max_val}"


# Singleton canonical transformer
canonical_transformer = CanonicalFeatureTransformer()
