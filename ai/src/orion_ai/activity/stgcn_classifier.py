"""PyTorch ST-GCN Activity Classifier implementing ActivityClassifierInterface."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, cast

import numpy as np
import torch

from orion_ai.activity.interfaces import ActivityClassifierInterface
from orion_ai.activity.registry import ActivityRegistry
from orion_ai.activity.schemas import (
    INDEX_TO_CLASS,
    TRAINED_ACTIVITY_CLASSES,
    ActivityPrediction,
    ActivityRecognitionResult,
    ActivityWindow,
    TemporalSkeletonPose,
    UncertaintyStatus,
)
from orion_ai.activity.stgcn.model import STGCNHARModel
from orion_ai.activity.stgcn.normalization import MicrogravityNormalizer

logger = logging.getLogger(__name__)


EXPECTED_TENSOR_NDIM_UNBATCHED: int = 3


class STGCNActivityClassifier(ActivityClassifierInterface):
    """Production-grade ST-GCN Spatio-Temporal Graph Convolutional HAR classifier."""

    def __init__(
        self,
        device: str = "cpu",
        confidence_threshold: float = 0.5,
        version: str = "1.0.0",
    ) -> None:
        self.device = torch.device(device)
        self.confidence_threshold = confidence_threshold
        self.version = version
        self.model: STGCNHARModel | None = None
        self.normalizer = MicrogravityNormalizer()
        self._lock = asyncio.Lock()
        self._is_loaded = False
        self._model_path: str | None = None
        self._classes: list[str] = list(TRAINED_ACTIVITY_CLASSES)
        self._idx_to_class: dict[int, str] = dict(INDEX_TO_CLASS)

    async def load(self, model_path: str) -> None:
        """Load ST-GCN weights, verify architecture and manifest if available, and warm up."""
        async with self._lock:
            p = Path(model_path)
            if not p.exists():
                raise FileNotFoundError(f"ST-GCN model weights not found at: {model_path}")

            # Check for manifest
            manifest_candidates = [
                p.with_name("model_manifest.json"),
                p.with_suffix(".manifest.json"),
            ]
            for mf_path in manifest_candidates:
                if mf_path.is_file():
                    import json

                    try:
                        with mf_path.open("r") as f:
                            m_data = json.load(f)
                        if "classes" in m_data and isinstance(m_data["classes"], list):
                            self._classes = m_data["classes"]
                            self._idx_to_class = {i: c for i, c in enumerate(self._classes)}
                            if "version" in m_data:
                                self.version = m_data["version"]
                            break
                    except Exception as exc:
                        logger.warning("Failed parsing manifest at %s: %s", mf_path, exc)

            num_classes = len(self._classes)

            def _load() -> STGCNHARModel:
                net = STGCNHARModel(in_channels=4, num_classes=num_classes)
                state_dict = torch.load(p, map_location=self.device)
                net.load_state_dict(state_dict)
                net.to(self.device)
                net.eval()
                # Warm up forward pass
                dummy = torch.zeros((1, 4, 32, 17), dtype=torch.float32, device=self.device)
                with torch.no_grad():
                    _ = net(dummy)
                return net

            self.model = await asyncio.to_thread(_load)
            self._model_path = str(p)
            self._is_loaded = True
            logger.info(
                "ST-GCN HAR model loaded successfully from %s on %s with %d classes",
                model_path,
                self.device,
                num_classes,
            )

    async def classify_window(
        self,
        sequence_or_tensor: list[TemporalSkeletonPose] | torch.Tensor | np.ndarray[Any, Any],
        window: ActivityWindow | None = None,
    ) -> ActivityRecognitionResult:
        """Run ST-GCN temporal inference under concurrency lock and offloaded threadpool."""
        if not self._is_loaded or self.model is None:
            raise RuntimeError("Cannot classify: ST-GCN model is not loaded.")

        model = self.model

        async with self._lock:
            t0 = time.perf_counter()

            # Preprocess to tensor of shape (1, 4, T, 17)
            if isinstance(sequence_or_tensor, torch.Tensor):
                tensor = sequence_or_tensor
                if tensor.ndim == EXPECTED_TENSOR_NDIM_UNBATCHED:
                    tensor = tensor.unsqueeze(0)
            elif isinstance(sequence_or_tensor, np.ndarray):
                tensor = torch.from_numpy(sequence_or_tensor).float()
                if tensor.ndim == EXPECTED_TENSOR_NDIM_UNBATCHED:
                    tensor = tensor.unsqueeze(0)
            elif isinstance(sequence_or_tensor, list):
                # List of TemporalSkeletonPose
                norm_feat, _ = self.normalizer.normalize_sequence(sequence_or_tensor)
                tensor = norm_feat.unsqueeze(0)
            else:
                raise TypeError(f"Unsupported sequence type: {type(sequence_or_tensor)}")

            def _infer(input_tensor: torch.Tensor) -> np.ndarray[Any, Any]:
                input_tensor = input_tensor.to(self.device)
                with torch.no_grad():
                    logits = model(input_tensor)
                    return cast(
                        "np.ndarray[Any, Any]", torch.softmax(logits, dim=1).cpu().numpy()[0]
                    )

            probabilities_arr = await asyncio.to_thread(_infer, tensor)
            latency_ms = (time.perf_counter() - t0) * 1000.0

            # Build prediction probability dict
            prob_dict: dict[str, float] = {
                self._idx_to_class.get(i, f"class_{i}"): float(probabilities_arr[i])
                for i in range(len(self._classes))
            }

            top_idx = int(np.argmax(probabilities_arr))
            top_class = self._idx_to_class.get(top_idx, f"class_{top_idx}")
            top_conf = float(probabilities_arr[top_idx])

            prediction = ActivityPrediction(
                activity_name=top_class,
                confidence=top_conf,
                probabilities=prob_dict,
                uncertainty_status=UncertaintyStatus.NOMINAL
                if top_conf >= self.confidence_threshold
                else UncertaintyStatus.UNCERTAIN,
                is_nominal=top_conf >= self.confidence_threshold,
                model_version=self.version,
            )

            candidates = [
                ActivityPrediction(
                    activity_name=cls,
                    confidence=float(prob),
                    probabilities={},
                    uncertainty_status=UncertaintyStatus.NOMINAL
                    if prob >= self.confidence_threshold
                    else UncertaintyStatus.UNCERTAIN,
                    is_nominal=prob >= self.confidence_threshold,
                    model_version=self.version,
                )
                for cls, prob in sorted(prob_dict.items(), key=lambda item: item[1], reverse=True)
            ]

            if window is None:
                track_id = 0
                if isinstance(sequence_or_tensor, list) and len(sequence_or_tensor) > 0:
                    track_id = sequence_or_tensor[-1].track_id
                window = ActivityWindow(
                    start_frame=0,
                    end_frame=32,
                    fps=30,
                    duration_seconds=32 / 30.0,
                    stride=8,
                    track_id=track_id,
                )

            return ActivityRecognitionResult(
                track_id=window.track_id,
                window=window,
                top_prediction=prediction,
                candidates=candidates,
                uncertainty_status=prediction.uncertainty_status,
                latency_ms=latency_ms,
            )

    async def unload(self) -> None:
        """Release PyTorch model memory."""
        async with self._lock:
            self.model = None
            self._is_loaded = False
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                torch.mps.empty_cache()
            logger.info("ST-GCN HAR model unloaded.")


# Register in factory registry
ActivityRegistry.register("stgcn_har_v1", STGCNActivityClassifier)
