"""Physically-valid kinetic skeleton augmentation pipeline for microgravity HAR.

Prevents overfitting on small-N spaceflight experiment datasets by applying
isometric kinematic transformations, temporal pacing variations, and sensor noise.
"""

from __future__ import annotations

import math

import numpy as np
import torch


class SkeletonKineticAugmenter:
    """Applies stochastic kinetic augmentations to (4, T, V) skeletal sequence tensors."""

    def __init__(
        self,
        noise_sigma: float = 0.012,
        scale_range: tuple[float, float] = (0.92, 1.08),
        max_rotation_deg: float = 12.0,
        temporal_stretch_range: tuple[float, float] = (0.85, 1.15),
        joint_dropout_prob: float = 0.05,
        prob_apply: float = 0.85,
    ) -> None:
        self.noise_sigma = noise_sigma
        self.scale_range = scale_range
        self.max_rotation_deg = max_rotation_deg
        self.temporal_stretch_range = temporal_stretch_range
        self.joint_dropout_prob = joint_dropout_prob
        self.prob_apply = prob_apply

    def __call__(self, x: np.ndarray | torch.Tensor) -> np.ndarray:
        """Apply augmentation pipeline to tensor of shape (4, 32, 17)."""
        if isinstance(x, torch.Tensor):  # noqa: SIM108
            arr = x.detach().cpu().numpy().copy()
        else:
            arr = x.copy()
        assert arr.shape == (4, 32, 17), f"Expected shape (4, 32, 17), got {arr.shape}"

        if np.random.rand() > self.prob_apply:
            return arr

        # 1. Random Joint Gaussian Noise
        if self.noise_sigma > 0:
            noise = np.random.normal(0.0, self.noise_sigma, size=arr[:2].shape).astype(np.float32)
            arr[0] = np.clip(arr[0] + noise[0], 0.0, 1.0)
            arr[1] = np.clip(arr[1] + noise[1], 0.0, 1.0)

        # 2. Random Centered Spatial Scaling (Simulates anthropometric variation)
        if self.scale_range:
            scale_factor = np.random.uniform(self.scale_range[0], self.scale_range[1])
            # Center of trunk: midpoint of left hip (11) and right hip (12) or nose (0)
            cx = np.mean(arr[0, :, [11, 12]]) if np.mean(arr[0, :, [11, 12]]) > 0 else 0.5
            cy = np.mean(arr[1, :, [11, 12]]) if np.mean(arr[1, :, [11, 12]]) > 0 else 0.5
            arr[0] = np.clip(cx + (arr[0] - cx) * scale_factor, 0.0, 1.0)
            arr[1] = np.clip(cy + (arr[1] - cy) * scale_factor, 0.0, 1.0)

        # 3. Random Planar Rotation (Simulates microgravity tilt)
        if self.max_rotation_deg > 0:
            angle_rad = math.radians(
                np.random.uniform(-self.max_rotation_deg, self.max_rotation_deg)
            )
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            cx = np.mean(arr[0])
            cy = np.mean(arr[1])
            x_shifted = arr[0] - cx
            y_shifted = arr[1] - cy
            arr[0] = np.clip(cx + x_shifted * cos_a - y_shifted * sin_a, 0.0, 1.0)
            arr[1] = np.clip(cy + x_shifted * sin_a + y_shifted * cos_a, 0.0, 1.0)

        # 4. Random Temporal Stretch / Compression (Pacing variations)
        if self.temporal_stretch_range:
            stretch = np.random.uniform(
                self.temporal_stretch_range[0], self.temporal_stretch_range[1]
            )
            orig_t = np.linspace(0, 1, 32)
            new_t = np.clip(np.linspace(0, 1 * stretch, 32), 0, 1)
            stretched = np.zeros_like(arr)
            for c in range(4):
                for v in range(17):
                    stretched[c, :, v] = np.interp(orig_t, new_t, arr[c, :, v])
            arr = np.clip(stretched, 0.0, 1.0)

        # 5. Joint Dropout (Sensor occlusion simulation)
        if self.joint_dropout_prob > 0:
            drop_mask = np.random.rand(17) < self.joint_dropout_prob
            # Do not drop wrists (9, 10) simultaneously to preserve interaction
            if drop_mask[9] and drop_mask[10]:
                drop_mask[np.random.choice([9, 10])] = False
            arr[:, :, drop_mask] = 0.0

        return arr
