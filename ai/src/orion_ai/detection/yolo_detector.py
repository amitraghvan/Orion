import asyncio
import time
from datetime import UTC, datetime
from typing import Any

import numpy as np
from ultralytics import YOLO  # type: ignore[attr-defined]

from orion.core.exceptions import InferenceError
from orion.core.logger import get_logger
from orion.health.interfaces import SubsystemReport, SubsystemStatus
from orion_ai.detection.interfaces import DetectorInterface
from orion_ai.detection.schemas import BoundingBox2D, DetectionResult, DetectionTarget

logger = get_logger("orion_ai.detection.yolo")


class YOLOEdgeDetector(DetectorInterface):
    """Real-time edge detector wrapping YOLO11 architectures."""

    IGNORED_CLASSES: set[str] = {
        "chair", "couch", "sofa", "bed", "dining table", "potted plant", "tv",
        "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
        "refrigerator", "toilet", "microwave", "oven", "toaster", "sink", "clock",
    }

    def __init__(
        self,
        confidence_threshold: float = 0.45,
        device: str | None = None,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.model: Any = None
        self._is_loaded: bool = False
        self._model_path: str | None = None
        self._inference_count: int = 0
        self._last_inference_utc: datetime | None = None
        self._last_latency_ms: float = 0.0
        self._last_error: str | None = None
        self._lock = asyncio.Lock()

    @property
    def is_loaded(self) -> bool:
        """Return whether model weights are allocated in memory."""
        return self._is_loaded

    async def load(self, model_path: str) -> None:
        """Load YOLO model weights and warm up inference runtime."""
        try:
            self._model_path = model_path
            self.model = await asyncio.to_thread(YOLO, model_path)

            # Auto-detect optimal execution provider if not specified
            if self.device is None:
                import torch

                if torch.cuda.is_available():
                    self.device = "cuda"
                elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    self.device = "mps"
                else:
                    self.device = "cpu"

            # Warmup pass in thread pool
            dummy = np.zeros((640, 640, 3), dtype=np.uint8)
            await asyncio.to_thread(self.model.predict, dummy, device=self.device, verbose=False)
            self._is_loaded = True
            self._last_error = None
            logger.info("YOLOEdgeDetector initialized", model=model_path, device=self.device)
        except Exception as exc:
            self._is_loaded = False
            self._last_error = str(exc)
            raise InferenceError(
                f"Failed to load YOLO model from {model_path}: {exc}",
                details={
                    "model_path": model_path,
                    "error": str(exc),
                    "subcode": "DETECTOR_LOAD_FAILURE",
                },
            ) from exc

    async def detect(self, frame_buffer: np.ndarray[Any, Any], frame_index: int) -> DetectionResult:
        """Execute forward pass on image buffer and return structured bounding boxes."""
        if not self._is_loaded or self.model is None:
            self._last_error = "Model not loaded"
            raise InferenceError(
                "Cannot execute detection: model is not loaded",
                details={"subcode": "DETECTOR_NOT_LOADED"},
            )

        try:
            async with self._lock:
                start_time = time.perf_counter()
                results: Any = await asyncio.to_thread(
                    self.model.predict,
                    source=frame_buffer,
                    conf=self.confidence_threshold,
                    device=self.device,
                    verbose=False,
                )

                targets: list[DetectionTarget] = []
                if results and len(results) > 0:
                    res: Any = results[0]
                    if res.boxes is not None and len(res.boxes) > 0:
                        xyxy = res.boxes.xyxy.cpu().numpy()
                        confs = res.boxes.conf.cpu().numpy()
                        cls_ids = res.boxes.cls.cpu().numpy().astype(int)

                        for box, conf, cls_id in zip(xyxy, confs, cls_ids, strict=False):
                            class_name = str(self.model.names.get(int(cls_id), f"class_{cls_id}"))
                            if class_name.lower() in self.IGNORED_CLASSES:
                                continue
                            if class_name.lower() != "person" and float(conf) < 0.40:
                                continue
                            targets.append(
                                DetectionTarget(
                                    class_id=int(cls_id),
                                    class_name=str(class_name),
                                    confidence=float(conf),
                                    box=BoundingBox2D(
                                        x_min=float(box[0]),
                                        y_min=float(box[1]),
                                        x_max=float(box[2]),
                                        y_max=float(box[3]),
                                    ),
                                )
                            )

                latency_ms = (time.perf_counter() - start_time) * 1000.0
                self._inference_count += 1
                self._last_inference_utc = datetime.now(UTC)
                self._last_latency_ms = latency_ms
                self._last_error = None
                return DetectionResult(
                    frame_index=frame_index,
                    timestamp_sensor_ns=time.time_ns(),
                    detections=targets,
                    inference_latency_ms=latency_ms,
                )
        except Exception as exc:
            self._last_error = str(exc)
            raise InferenceError(
                f"Inference execution failed on frame {frame_index}: {exc}",
                details={
                    "frame_index": frame_index,
                    "error": str(exc),
                    "subcode": "DETECTOR_INFERENCE_ERROR",
                },
            ) from exc

    async def unload(self) -> None:
        """Release model weights and context."""
        self.model = None
        self._is_loaded = False
        logger.info("YOLOEdgeDetector unloaded")

    def get_health_report(self) -> SubsystemReport:
        """Return standardized subsystem health diagnostic report."""
        now = datetime.now(UTC)
        if not self._is_loaded:
            status = SubsystemStatus.OFFLINE
            err = self._last_error or "Model weights not loaded in memory"
        elif self._last_error:
            status = SubsystemStatus.DEGRADED
            err = f"Last inference failed: {self._last_error}"
        else:
            status = SubsystemStatus.HEALTHY
            err = None

        return SubsystemReport(
            subsystem_id="detector",
            status=status,
            timestamp=now,
            last_success=self._last_inference_utc,
            latency_ms=self._last_latency_ms,
            metrics={
                "inferences_total": self._inference_count,
                "is_loaded": self._is_loaded,
                "confidence_threshold": self.confidence_threshold,
            },
            details={
                "device": self.device or "auto",
                "model_configured": True,
            },
            error_message=err,
        )
