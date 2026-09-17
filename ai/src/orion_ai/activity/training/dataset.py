"""PyTorch Dataset and Controlled Synthetic Kinematic Motion Generator for HAR training/validation."""

from dataclasses import dataclass

import numpy as np
import torch
from torch.utils.data import Dataset

from orion_ai.activity.schemas import CLASS_TO_INDEX, TRAINED_ACTIVITY_CLASSES

NUM_JOINTS: int = 17


@dataclass
class SyntheticSampleMetadata:
    """Provenance metadata ensuring synthetic data is never represented as domain evidence."""

    generator_version: str
    seed: int
    activity_name: str
    class_id: int
    source: str = "synthetic"
    num_frames: int = 32


class SyntheticKinematicGenerator:
    """Deterministic kinematic motion generator for smoke training, pipeline validation, and augmentation."""

    def __init__(self, num_frames: int = 32, seed: int = 42) -> None:
        self.num_frames = num_frames
        self.rng = np.random.default_rng(seed)
        self.generator_version = "1.0.0"

    def generate_sample(
        self,
        class_name: str,
        seed: int | None = None,
    ) -> tuple[torch.Tensor, int, SyntheticSampleMetadata]:
        """Generate a single normalized (C=4, T, V=17) tensor and class label.

        Kinematic definitions:
        - prepare_workstation (0): Bilateral cyclic arm motions (wiping / hatch prep).
        - reach_tool (1): Right wrist and elbow extension forward/upward.
        - grasp_tool (2): Wrist held stationary at target tool location, micro-movements.
        - manipulate_sample (3): Cyclic vertical pipetting aspiration/injection oscillations.
        - inspect_chamber (4): Torso forward lean, head downward tilt, arms held steady.
        - idle (5): Passive microgravity float, minimal joint displacement.
        """
        rng = np.random.default_rng(seed) if seed is not None else self.rng
        class_idx = CLASS_TO_INDEX[class_name]
        T = self.num_frames
        V = NUM_JOINTS

        # Canonical baseline centered joint positions (X, Y)
        base_coords = np.zeros((V, 2), dtype=np.float32)
        base_coords[0] = [0.0, 0.5]  # nose
        base_coords[1] = [-0.1, 0.55]  # l_eye
        base_coords[2] = [0.1, 0.55]  # r_eye
        base_coords[3] = [-0.2, 0.5]  # l_ear
        base_coords[4] = [0.2, 0.5]  # r_ear
        base_coords[5] = [-0.4, 0.35]  # l_shoulder
        base_coords[6] = [0.4, 0.35]  # r_shoulder
        base_coords[7] = [-0.5, 0.0]  # l_elbow
        base_coords[8] = [0.5, 0.0]  # r_elbow
        base_coords[9] = [-0.5, -0.3]  # l_wrist
        base_coords[10] = [0.5, -0.3]  # r_wrist
        base_coords[11] = [-0.2, -0.2]  # l_hip
        base_coords[12] = [0.2, -0.2]  # r_hip
        base_coords[13] = [-0.2, -0.6]  # l_knee
        base_coords[14] = [0.2, -0.6]  # r_knee
        base_coords[15] = [-0.2, -1.0]  # l_ankle
        base_coords[16] = [0.2, -1.0]  # r_ankle

        # Tile across time: (T, V, 2)
        coords = np.tile(base_coords[np.newaxis, :, :], (T, 1, 1))

        # Add class-specific kinematic trajectories
        t = np.linspace(0, 2 * np.pi, T)

        if class_name == "prepare_workstation":
            # Bilateral wiping / sweeping motion
            coords[:, 9, 0] += 0.3 * np.sin(2 * t)
            coords[:, 9, 1] += 0.2 * np.cos(2 * t)
            coords[:, 10, 0] -= 0.3 * np.sin(2 * t)
            coords[:, 10, 1] += 0.2 * np.cos(2 * t)
        elif class_name == "reach_tool":
            # Right arm reaches forward and upward
            progress = np.linspace(0.0, 0.6, T)
            coords[:, 8, 0] += progress * 0.4
            coords[:, 8, 1] += progress * 0.5
            coords[:, 10, 0] += progress * 0.8
            coords[:, 10, 1] += progress * 0.7
        elif class_name == "grasp_tool":
            # Right hand held at tool position with subtle stabilization jitter
            coords[:, 10, 0] += 0.4 + 0.02 * np.sin(4 * t)
            coords[:, 10, 1] += 0.3 + 0.02 * np.cos(4 * t)
        elif class_name == "manipulate_sample":
            # Pipette plunger aspiration/dispense: cyclic vertical hand oscillation
            coords[:, 10, 0] += 0.3
            coords[:, 10, 1] += 0.2 + 0.15 * np.sin(3 * t)
        elif class_name == "inspect_chamber":
            # Torso leaned forward, head down, steady hands
            coords[:, 0, 1] -= 0.1  # nose lower
            coords[:, :, 1] -= 0.05
        elif class_name == "idle":
            # Low frequency gentle microgravity sway
            sway = 0.03 * np.sin(0.5 * t)
            coords[:, :, 0] += sway[:, np.newaxis]

        # Add slight observation noise (scale ~0.01)
        noise = rng.normal(0.0, 0.015, size=coords.shape).astype(np.float32)
        coords += noise

        # Calculate motion velocity: (T, V, 2)
        vel = np.zeros_like(coords)
        vel[1:] = coords[1:] - coords[:-1]

        # Pack into (C=4, T, V=17)
        features = np.zeros((4, T, V), dtype=np.float32)
        features[0] = coords[:, :, 0]
        features[1] = coords[:, :, 1]
        features[2] = vel[:, :, 0]
        features[3] = vel[:, :, 1]

        metadata = SyntheticSampleMetadata(
            generator_version=self.generator_version,
            seed=seed if seed is not None else 42,
            activity_name=class_name,
            class_id=class_idx,
            num_frames=T,
        )

        return torch.from_numpy(features), class_idx, metadata


class SkeletonActionDataset(Dataset[tuple[torch.Tensor, int]]):
    """PyTorch dataset for skeleton temporal action sequences."""

    def __init__(
        self,
        samples: list[torch.Tensor],
        labels: list[int],
        metadata_list: list[SyntheticSampleMetadata] | None = None,
    ) -> None:
        self.samples = samples
        self.labels = labels
        self.metadata_list = metadata_list or []

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        return self.samples[idx], self.labels[idx]


def build_synthetic_dataset(
    samples_per_class: int = 100,
    num_frames: int = 32,
    base_seed: int = 42,
) -> tuple[SkeletonActionDataset, SkeletonActionDataset]:
    """Generate reproducible train and validation synthetic datasets."""
    generator = SyntheticKinematicGenerator(num_frames=num_frames, seed=base_seed)

    train_samples: list[torch.Tensor] = []
    train_labels: list[int] = []
    train_meta: list[SyntheticSampleMetadata] = []

    val_samples: list[torch.Tensor] = []
    val_labels: list[int] = []
    val_meta: list[SyntheticSampleMetadata] = []

    val_split_ratio = 0.2
    n_val = int(samples_per_class * val_split_ratio)
    n_train = samples_per_class - n_val

    for class_name in TRAINED_ACTIVITY_CLASSES:
        for i in range(samples_per_class):
            sample_seed = base_seed + hash(class_name) % 10000 + i * 7
            feat, label, meta = generator.generate_sample(class_name, seed=sample_seed)

            if i < n_train:
                train_samples.append(feat)
                train_labels.append(label)
                train_meta.append(meta)
            else:
                val_samples.append(feat)
                val_labels.append(label)
                val_meta.append(meta)

    train_ds = SkeletonActionDataset(train_samples, train_labels, train_meta)
    val_ds = SkeletonActionDataset(val_samples, val_labels, val_meta)
    return train_ds, val_ds
