import asyncio
import time
from datetime import UTC, datetime
from typing import Any

import numpy as np
from ultralytics import YOLO  # type: ignore[attr-defined]

from orion.core.exceptions import InferenceError
from orion.core.logger import get_logger
from orion.health.interfaces import SubsystemReport, SubsystemStatus
from orion_ai.detection.schemas import BoundingBox2D, DetectionResult
from orion_ai.pose.interfaces import PoseEstimatorInterface
from orion_ai.pose.schemas import HumanPose, Keypoint2D, PoseEstimationResult

logger = get_logger("orion_ai.pose.yolo")

COCO_KEYPOINT_NAMES = [
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]

MIN_KEYPOINT_CONFIDENCE: float = 0.2


class YOLOPoseEstimator(PoseEstimatorInterface):
    """Real-time edge pose estimator extracting 17-point COCO whole-body skeletons."""

    def __init__(
        self,
        confidence_threshold: float = 0.35,
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
        """Return whether pose weights are allocated in memory."""
        return self._is_loaded

    async def load(self, model_path: str) -> None:
        """Initialize pose estimation model weights and runtime context."""
        try:
            self._model_path = model_path
            self.model = await asyncio.to_thread(YOLO, model_path)

            # Detect hardware acceleration device
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
            logger.info("YOLOPoseEstimator initialized", model=model_path, device=self.device)
        except Exception as exc:
            self._is_loaded = False
            self._last_error = str(exc)
            raise InferenceError(
                f"Failed to load YOLO pose model from {model_path}: {exc}",
                details={
                    "model_path": model_path,
                    "error": str(exc),
                    "subcode": "POSE_LOAD_FAILURE",
                },
            ) from exc

    async def estimate(
        self, frame_buffer: np.ndarray[Any, Any], detections: DetectionResult | None = None
    ) -> PoseEstimationResult:
        """Extract 17-point whole-body 2D keypoints from optical frame buffer."""
        if not self._is_loaded or self.model is None:
            self._last_error = "Model not loaded"
            raise InferenceError(
                "Cannot execute pose estimation: model is not loaded",
                details={"subcode": "POSE_NOT_LOADED"},
            )

        try:
            async with self._lock:
                start_time = time.perf_counter()
                frame_idx = detections.frame_index if detections else 0

                results: Any = await asyncio.to_thread(
                    self.model.predict,
                    source=frame_buffer,
                    conf=self.confidence_threshold,
                    device=self.device,
                    verbose=False,
                )

                poses: list[HumanPose] = []
                if results and len(results) > 0:
                    res: Any = results[0]
                    if res.keypoints is not None and len(res.keypoints) > 0:
                        xy_all = res.keypoints.xy.cpu().numpy()  # shape (N, 17, 2)
                        conf_all = (
                            res.keypoints.conf.cpu().numpy()
                            if res.keypoints.conf is not None
                            else np.ones((len(xy_all), 17))
                        )
                        boxes = res.boxes.xyxy.cpu().numpy() if res.boxes is not None else None

                        candidate_poses: list[HumanPose] = []
                        for person_idx, (kps, scores) in enumerate(
                            zip(xy_all, conf_all, strict=False)
                        ):
                            valid_kps = [score for score in scores if score >= 0.25]
                            # Require at least 6 confident keypoints to form a valid human body
                            if len(valid_kps) < 6:
                                continue

                            keypoints_2d: list[Keypoint2D] = []
                            for kp_idx, (pt, score) in enumerate(zip(kps, scores, strict=False)):
                                name = (
                                    COCO_KEYPOINT_NAMES[kp_idx]
                                    if kp_idx < len(COCO_KEYPOINT_NAMES)
                                    else f"kp_{kp_idx}"
                                )
                                keypoints_2d.append(
                                    Keypoint2D(
                                        id=kp_idx,
                                        name=name,
                                        x=float(pt[0]),
                                        y=float(pt[1]),
                                        score=float(np.clip(score, 0.0, 1.0)),
                                    )
                                )

                            # Bounding box for this skeleton
                            if boxes is not None and person_idx < len(boxes):
                                b = boxes[person_idx]
                                bbox = BoundingBox2D(
                                    x_min=float(b[0]),
                                    y_min=float(b[1]),
                                    x_max=float(b[2]),
                                    y_max=float(b[3]),
                                )
                            else:
                                valid_pts = kps[scores > MIN_KEYPOINT_CONFIDENCE]
                                if len(valid_pts) > 0:
                                    bbox = BoundingBox2D(
                                        x_min=float(np.min(valid_pts[:, 0])),
                                        y_min=float(np.min(valid_pts[:, 1])),
                                        x_max=float(np.max(valid_pts[:, 0])),
                                        y_max=float(np.max(valid_pts[:, 1])),
                                    )
                                else:
                                    bbox = BoundingBox2D(x_min=0.0, y_min=0.0, x_max=0.0, y_max=0.0)

                            overall_conf = float(np.mean(scores)) if len(scores) > 0 else 0.0
                            if overall_conf < 0.30:
                                continue

                            candidate_poses.append(
                                HumanPose(
                                    person_id=person_idx + 1,
                                    bbox=bbox,
                                    topology="coco_17",
                                    keypoints_2d=keypoints_2d,
                                    overall_confidence=overall_conf,
                                )
                            )

                        # Sort candidate poses by overall confidence
                        candidate_poses.sort(key=lambda p: p.overall_confidence, reverse=True)

                        # Non-Maximum Suppression on poses to eliminate duplicate overlapping skeletons on the same person
                        for cand in candidate_poses:
                            b1 = cand.bbox
                            overlap = False
                            for accepted in poses:
                                b2 = accepted.bbox
                                xi1 = max(b1.x_min, b2.x_min)
                                yi1 = max(b1.y_min, b2.y_min)
                                xi2 = min(b1.x_max, b2.x_max)
                                yi2 = min(b1.y_max, b2.y_max)
                                inter = max(0.0, xi2 - xi1) * max(0.0, yi2 - yi1)
                                a1 = max(0.0, b1.x_max - b1.x_min) * max(0.0, b1.y_max - b1.y_min)
                                a2 = max(0.0, b2.x_max - b2.x_min) * max(0.0, b2.y_max - b2.y_min)
                                iou = inter / (a1 + a2 - inter + 1e-6)
                                if iou > 0.40:
                                    overlap = True
                                    break
                            if not overlap:
                                cand.person_id = len(poses) + 1
                                poses.append(cand)
                                if len(poses) >= 2:
                                    break

                latency_ms = (time.perf_counter() - start_time) * 1000.0
                self._inference_count += 1
                self._last_inference_utc = datetime.now(UTC)
                self._last_latency_ms = latency_ms
                self._last_error = None
                return PoseEstimationResult(
                    frame_index=frame_idx,
                    poses=poses,
                    inference_time_ms=latency_ms,
                )
        except Exception as exc:
            self._last_error = str(exc)
            raise InferenceError(
                f"Pose estimation failed on frame {frame_idx}: {exc}",
                details={
                    "frame_index": frame_idx,
                    "error": str(exc),
                    "subcode": "POSE_INFERENCE_ERROR",
                },
            ) from exc

    async def unload(self) -> None:
        """Release pose weights and runtime context."""
        self.model = None
        self._is_loaded = False
        logger.info("YOLOPoseEstimator unloaded")

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
            subsystem_id="pose",
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
                "topology": "coco_17",
                "model_configured": True,
            },
            error_message=err,
        )
