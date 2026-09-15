"""Object detector for protocol-relevant instruments and experiment hardware."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

import numpy as np
from ultralytics import YOLO  # type: ignore[attr-defined]

from orion.core.exceptions import InferenceError
from orion.core.logger import get_logger
from orion_ai.detection.interfaces import DetectorInterface
from orion_ai.detection.schemas import BoundingBox2D, DetectionResult, DetectionTarget
from orion_ai.interaction.object_schemas import ObjectObservation
from orion_ai.tracking.schemas import TrackedObject

logger = get_logger("orion_ai.detection.object")

DEFAULT_PROTOCOL_CLASSES: set[str] = {
    # Canonical BAS protocol items
    "tool_pipette_p1000",
    "sample_cassette_a",
    "centrifuge_tube_15ml",
    # Aliases and generic vocabulary
    "pipette",
    "cassette",
    "tube",
    "bottle",
    "cup",
    "scissors",
    "tool",
    "container",
    "instrument",
}


class ObjectDetector(DetectorInterface):
    """Secondary YOLO detector dedicated to protocol tools, consumables, and chambers."""

    def __init__(
        self,
        confidence_threshold: float = 0.3,
        device: str | None = None,
        target_classes: set[str] | list[str] | None = None,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.target_classes = set(target_classes) if target_classes is not None else DEFAULT_PROTOCOL_CLASSES
        self.model: Any = None
        self._is_loaded: bool = False
        self._model_path: str | None = None
        self._lock = asyncio.Lock()

    @property
    def is_loaded(self) -> bool:
        """Return whether model weights are allocated in memory."""
        return self._is_loaded

    async def load(self, model_path: str) -> None:
        """Load object detector weights and initialize execution provider."""
        try:
            self._model_path = model_path
            self.model = await asyncio.to_thread(YOLO, model_path)

            if self.device is None:
                import torch

                if torch.cuda.is_available():
                    self.device = "cuda"
                elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    self.device = "mps"
                else:
                    self.device = "cpu"

            dummy = np.zeros((640, 640, 3), dtype=np.uint8)
            await asyncio.to_thread(self.model.predict, dummy, device=self.device, verbose=False)
            self._is_loaded = True
            logger.info("ObjectDetector initialized", model=model_path, device=self.device)
        except Exception as exc:
            self._is_loaded = False
            raise InferenceError(
                f"Failed to load object detector model from {model_path}: {exc}",
                details={
                    "model_path": model_path,
                    "error": str(exc),
                    "subcode": "OBJECT_DETECTOR_LOAD_FAILURE",
                },
            ) from exc

    async def detect(self, frame_buffer: np.ndarray[Any, Any], frame_index: int) -> DetectionResult:
        """Execute forward pass on image buffer and return protocol object detections."""
        if not self._is_loaded or self.model is None:
            raise InferenceError(
                "Cannot execute object detection: model is not loaded",
                details={"subcode": "OBJECT_DETECTOR_NOT_LOADED"},
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
                            raw_name = str(self.model.names.get(int(cls_id), f"class_{cls_id}"))
                            class_name = raw_name.lower().strip()

                            # Exclude person detections from object detector
                            if class_name == "person":
                                continue

                            # If target classes are defined, filter against them
                            if self.target_classes and class_name not in self.target_classes:
                                continue

                            targets.append(
                                DetectionTarget(
                                    class_id=int(cls_id),
                                    class_name=class_name,
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
                return DetectionResult(
                    frame_index=frame_index,
                    timestamp_sensor_ns=time.time_ns(),
                    detections=targets,
                    inference_latency_ms=latency_ms,
                )
        except Exception as exc:
            raise InferenceError(
                f"Object detection inference failed on frame {frame_index}: {exc}",
                details={
                    "frame_index": frame_index,
                    "error": str(exc),
                    "subcode": "OBJECT_DETECTOR_INFERENCE_ERROR",
                },
            ) from exc

    async def unload(self) -> None:
        """Release model weights and context."""
        self.model = None
        self._is_loaded = False
        logger.info("ObjectDetector unloaded")


def tracked_objects_to_observations(
    tracks: list[TrackedObject],
    frame_index: int,
    timestamp: datetime | None = None,
    source_id: str = "primary_payload_camera",
) -> list[ObjectObservation]:
    """Convert tracked non-person objects into structured ObjectObservation instances."""
    if timestamp is None:
        timestamp = datetime.now(UTC)

    observations: list[ObjectObservation] = []
    for trk in tracks:
        if trk.class_name.lower() == "person" or trk.class_id == 0:
            continue
        observations.append(
            ObjectObservation(
                object_id=f"obj_{trk.class_name}_{trk.track_id}",
                class_name=trk.class_name,
                bbox=trk.box,
                confidence=trk.confidence,
                track_id=trk.track_id,
                frame_index=frame_index,
                timestamp=timestamp,
                source_id=source_id,
            )
        )
    return observations
