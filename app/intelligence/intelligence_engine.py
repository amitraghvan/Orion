"""Master perception pipeline coordinator integrating Detection, Pose, Tracking, HOI, and HAR."""

from __future__ import annotations

import time
from typing import Any

import cv2
import numpy as np

from app.core.config import get_config
from app.core.event_bus import event_bus
from app.core.logging import get_logger
from app.core.state_manager import PerceptionSnapshot, state_manager
from app.intelligence.hand_object_engine import HandObjectInteractionEngine
from app.intelligence.pose_estimator import PoseEstimatorWrapper
from app.intelligence.temporal_engine import TemporalHAREngine
from app.intelligence.tracker import ObjectTrackerWrapper
from app.models.model_manager import model_manager

logger = get_logger("app.intelligence.engine")


class IntelligenceEngine:
    """Coordinates real-time deep learning inference and multimodal perception pipeline."""

    def __init__(self) -> None:
        self.tracker = ObjectTrackerWrapper()
        self.pose_estimator = PoseEstimatorWrapper()
        self.hoi_engine = HandObjectInteractionEngine()
        self.har_engine = TemporalHAREngine(window_size=32)

        self._frame_count = 0
        self._fps_timer = time.monotonic()
        self._inference_fps = 0.0
        self._last_latency_ms = 0.0

    def initialize_models(self) -> bool:
        """Load default perception models defined in configuration."""
        cfg = get_config()
        logger.info("Initializing intelligence models...")

        # 1. Detection model (YOLO11n)
        model_manager.load_model(
            name="detection",
            model_path=cfg.models.detection.path,
            backend_type=cfg.models.detection.backend,
            device=cfg.models.detection.device,
        )

        # 2. Pose model (YOLO11n-pose)
        model_manager.load_model(
            name="pose",
            model_path=cfg.models.pose.path,
            backend_type=cfg.models.pose.backend,
            device=cfg.models.pose.device,
        )

        # 3. HAR model (ST-GCN)
        model_manager.load_model(
            name="activity",
            model_path=cfg.models.activity.path,
            backend_type=cfg.models.activity.backend,
            device=cfg.models.activity.device,
        )

        return True

    def process_frame(self, frame_bgr: np.ndarray, frame_id: int, timestamp: float) -> PerceptionSnapshot:
        """Execute complete perception pipeline on a single video frame."""
        t0 = time.perf_counter()
        self._frame_count += 1

        detected_objects: list[dict] = []
        poses: list[dict] = []
        hands: list[dict] = []
        interactions: list[dict] = []

        # 1. Object Detection
        det_backend = model_manager.get_model("detection")
        if det_backend is not None and det_backend.is_loaded:
            try:
                results = det_backend.predict(frame_bgr)
                if results and len(results) > 0:
                    r = results[0]
                    boxes = r.boxes.xyxy.cpu().numpy()
                    confs = r.boxes.conf.cpu().numpy()
                    cls_ids = r.boxes.cls.cpu().numpy()
                    names = r.names

                    raw_dets = []
                    for i in range(len(boxes)):
                        cid = int(cls_ids[i])
                        cname = names.get(cid, str(cid)) if isinstance(names, dict) else str(cid)
                        raw_dets.append({
                            "bbox": boxes[i].tolist(),
                            "confidence": float(confs[i]),
                            "class_id": cid,
                            "class_name": cname,
                        })

                    # Track detections
                    detected_objects = self.tracker.update(raw_dets)
            except Exception as exc:
                logger.error("Detection error in frame", error=str(exc))

        # 2. Pose Estimation
        pose_backend = model_manager.get_model("pose")
        if pose_backend is not None and pose_backend.is_loaded:
            try:
                poses = self.pose_estimator.estimate(pose_backend, frame_bgr)
            except Exception as exc:
                logger.error("Pose error in frame", error=str(exc))

        # 3. Hand Extraction & HOI Interaction
        interaction_score = 0.0
        if poses:
            hands = self.hoi_engine.extract_hands(poses)
            if hands and detected_objects:
                interactions = self.hoi_engine.evaluate_interactions(hands, detected_objects)
                if interactions:
                    interaction_score = max(float(i.get("confidence", 0.5)) for i in interactions)

        # 4. Temporal HAR (ST-GCN)
        primary_kpts = poses[0]["keypoints"] if poses else None
        fh, fw = frame_bgr.shape[:2]
        self.har_engine.push_frame_keypoints(
            primary_kpts,
            frame_width=float(fw),
            frame_height=float(fh),
            interaction_score=float(interaction_score),
        )

        har_backend = model_manager.get_model("activity")
        har_res = self.har_engine.predict_activity(har_backend)

        # 5. Measure Latency & Throughput
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self._last_latency_ms = elapsed_ms

        now = time.monotonic()
        if (now - self._fps_timer) >= 1.0:
            self._inference_fps = self._frame_count / (now - self._fps_timer)
            self._frame_count = 0
            self._fps_timer = now

            state_manager.update_telemetry(
                inference_fps=round(self._inference_fps, 1),
                inference_latency_ms=round(elapsed_ms, 2),
                total_frames_processed=frame_id,
            )

        # 6. Construct Snapshot
        snapshot = PerceptionSnapshot(
            frame_index=frame_id,
            detected_objects=detected_objects,
            poses=poses,
            hands=hands,
            interactions=interactions,
            recognized_activity=har_res.get("activity", "idle"),
            activity_confidence=har_res.get("confidence", 0.0),
            activity_entropy=har_res.get("entropy", 0.0),
            uncertainty_status=har_res.get("uncertainty_status", "NOMINAL"),
        )

        state_manager.set_perception_snapshot(snapshot)
        return snapshot


# Global intelligence engine singleton
intelligence_engine = IntelligenceEngine()
