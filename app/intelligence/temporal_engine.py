"""Spatio-Temporal Graph Convolutional Network (ST-GCN) temporal activity engine."""

from __future__ import annotations

import math
from collections import deque
from typing import Any

import numpy as np
import torch
from app.core.logging import get_logger

logger = get_logger("app.intelligence.temporal")

# Canonical class labels
BAS_HAR_CLASSES_8 = [
    "idle",
    "pick_yellow",
    "place_yellow",
    "pick_red",
    "place_red",
    "move_box",
    "check_box",
    "overlap_boxes",
]

BAS_HAR_CLASSES_6 = [
    "prepare_workstation",
    "reach_tool",
    "grasp_tool",
    "manipulate_sample",
    "inspect_chamber",
    "idle",
]


class TemporalHAREngine:
    """Maintains a 32-frame sliding buffer of COCO-17 keypoints and classifies temporal actions."""

    def __init__(self, window_size: int = 32, num_joints: int = 17) -> None:
        self.window_size = window_size
        self.num_joints = num_joints
        self._keypoint_buffer: deque[np.ndarray] = deque(maxlen=window_size)
        self._classes = BAS_HAR_CLASSES_8
        self._recent_predictions: deque[str] = deque(maxlen=5)
        # Import canonical transformer
        from orion_ai.activity.feature_transformer import canonical_transformer

        self.transformer = canonical_transformer

    def set_classes(self, classes: list[str]) -> None:
        self._classes = classes

    def push_frame_keypoints(
        self,
        keypoints: np.ndarray | None,
        frame_width: float = 640.0,
        frame_height: float = 480.0,
        interaction_score: float = 0.0,
    ) -> None:
        """Push a single frame's transformed (4, 17) features into the temporal window."""
        feat = self.transformer.transform_frame(
            keypoints=keypoints,
            frame_width=frame_width,
            frame_height=frame_height,
            interaction_score=interaction_score,
        )
        self._keypoint_buffer.append(feat)

    def is_buffer_full(self) -> bool:
        return len(self._keypoint_buffer) == self.window_size

    def predict_activity(self, model_backend: Any) -> dict[str, Any]:
        """Run ST-GCN forward inference on current temporal window."""
        if not self.is_buffer_full() or model_backend is None or not model_backend.is_loaded:
            return {
                "activity": "idle",
                "confidence": 0.5,
                "entropy": 0.0,
                "uncertainty_status": "WAITING_FOR_EVIDENCE",
                "probabilities": {c: (1.0 if c == "idle" else 0.0) for c in self._classes},
            }

        try:
            # Prepare tensor shape: (1, 4, 32, 17)
            # Channels: x_norm, y_norm, confidence, interaction
            # Stack 32 frames of (4, 17) along time dimension -> (4, 32, 17)
            stacked = np.stack(list(self._keypoint_buffer), axis=1)  # (4, 32, 17)
            tensor_np = np.expand_dims(stacked, axis=0).astype(np.float32)  # (1, 4, 32, 17)

            # Invariant check
            self.transformer.validate_tensor(tensor_np)

            # Forward inference
            logits = model_backend.predict(tensor_np)

            if isinstance(logits, torch.Tensor):
                logits_np = logits.detach().cpu().numpy().flatten()
            elif isinstance(logits, (list, tuple)):
                logits_np = np.array(logits[0]).flatten()
            else:
                logits_np = np.array(logits).flatten()

            # Softmax
            exp_logits = np.exp(logits_np - np.max(logits_np))
            probs = exp_logits / (np.sum(exp_logits) + 1e-9)

            # Shannon entropy: H = -sum(p * log2(p))
            entropy = 0.0
            for p in probs:
                if p > 1e-6:
                    entropy -= p * math.log2(p)

            # Determine class
            num_classes = min(len(probs), len(self._classes))
            top_idx = int(np.argmax(probs[:num_classes]))
            top_class = self._classes[top_idx]
            top_conf = float(probs[top_idx])

            # Uncertainty calibration
            status = "NOMINAL"
            if top_conf < 0.65 or entropy > 1.40:
                status = "UNCERTAIN"

            self._recent_predictions.append(top_class)

            prob_dict = {self._classes[i]: float(probs[i]) for i in range(num_classes)}

            return {
                "activity": top_class,
                "confidence": round(top_conf, 3),
                "entropy": round(entropy, 3),
                "uncertainty_status": status,
                "probabilities": prob_dict,
            }
        except Exception as exc:
            logger.error("ST-GCN prediction failed", error=str(exc))
            return {
                "activity": "idle",
                "confidence": 0.5,
                "entropy": 0.0,
                "uncertainty_status": "ERROR",
                "probabilities": {"idle": 1.0},
            }

    def reset(self) -> None:
        self._keypoint_buffer.clear()
        self._recent_predictions.clear()
