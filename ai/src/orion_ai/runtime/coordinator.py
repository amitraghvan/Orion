"""Real-time perception pipeline coordinator linking Camera, Detection, Pose, and Tracking for ORION BAS AI Copilot."""

import asyncio
import base64
import contextlib
import time
from collections import deque
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

from orion.core.event_bus import EventBusInterface
from orion.core.logger import get_logger
from orion.core.metrics import (
    FRAMES_FAILED_TOTAL,
    FRAMES_PROCESSED_TOTAL,
    FRAMES_RECEIVED_TOTAL,
    INFERENCE_LATENCY_AVG_MS,
    INFERENCE_LATENCY_MS,
    OBSERVATIONS_PUBLISHED_TOTAL,
    PIPELINE_ERRORS_TOTAL,
)
from orion.events.schemas import (
    DetectionCompleted,
    FrameCaptured,
    HealthChanged,
    MultimodalEvidenceUpdated,
    ObservationCaptured,
    PoseCompleted,
)
from orion.health.interfaces import SubsystemReport, SubsystemStatus
from orion_ai.activity.runtime import TemporalHARRuntime
from orion_ai.camera.interfaces import CameraDriverInterface
from orion_ai.detection.interfaces import DetectorInterface
from orion_ai.detection.object_detector import tracked_objects_to_observations
from orion_ai.detection.schemas import BoundingBox2D, DetectionResult, DetectionTarget
from orion_ai.geometry.iou import compute_bbox_iou
from orion_ai.hand.extractor import PoseBasedHandExtractor
from orion_ai.hand.interfaces import HandPerceptionInterface
from orion_ai.hand.schemas import HandObservation
from orion_ai.interaction.fusion import DeterministicMultimodalFusion
from orion_ai.interaction.hand_object_associator import HandObjectAssociator
from orion_ai.interaction.multimodal_schemas import (
    InteractionObservation,
    MultimodalActivityEvidence,
)
from orion_ai.interaction.object_schemas import ObjectObservation
from orion_ai.interaction.state_machine import InteractionStateMachine
from orion_ai.pose.interfaces import PoseEstimatorInterface
from orion_ai.pose.schemas import HumanPose
from orion_ai.runtime.observation import PipelineMetrics, StructuredObservation
from orion_ai.tracking.interfaces import TrackerInterface
from orion_ai.tracking.schemas import TrackedObject

if TYPE_CHECKING:
    from orion_ai.activity.schemas import ActivityRecognitionResult


logger = get_logger("orion_ai.runtime.coordinator")

FPS_HISTORY_WINDOW: int = 30

_compute_bbox_iou = compute_bbox_iou


def _associate_poses_with_tracks(
    poses: list[HumanPose],
    tracks: list[TrackedObject],
    min_iou_thresh: float = 0.2,
) -> None:
    """Associate detected poses with tracked person identities via Hungarian matching."""
    if not poses:
        return

    person_tracks = [t for t in tracks if t.class_id == 0 or t.class_name.lower() == "person"]

    if not person_tracks:
        for p_idx, pose in enumerate(poses):
            pose.person_id = p_idx + 1
        return

    n_poses = len(poses)
    m_tracks = len(person_tracks)

    cost_matrix = np.ones((n_poses, m_tracks), dtype=np.float32)
    for i, pose in enumerate(poses):
        for j, trk in enumerate(person_tracks):
            cost_matrix[i, j] = 1.0 - compute_bbox_iou(pose.bbox, trk.box)

    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    matched_poses: set[int] = set()
    for r, c in zip(row_ind, col_ind, strict=False):
        iou = 1.0 - float(cost_matrix[r, c])
        if iou >= min_iou_thresh:
            poses[r].person_id = person_tracks[c].track_id
            matched_poses.add(r)
        else:
            poses[r].person_id = r + 1
            matched_poses.add(r)

    for r, pose in enumerate(poses):
        if r not in matched_poses:
            pose.person_id = r + 1


class PerceptionPipelineCoordinator:
    """Orchestrates sequential multi-modal perception DAG with isolated stage failure containment."""

    def __init__(
        self,
        camera: CameraDriverInterface,
        detector: DetectorInterface,
        pose_estimator: PoseEstimatorInterface,
        tracker: TrackerInterface,
        event_bus: EventBusInterface,
        station_id: str = "BAS-NODE-01",
        har_runtime: TemporalHARRuntime | None = None,
        object_detector: DetectorInterface | None = None,
        hand_extractor: HandPerceptionInterface | None = None,
        interaction_associator: HandObjectAssociator | None = None,
        interaction_state_machine: InteractionStateMachine | None = None,
        multimodal_fusion: DeterministicMultimodalFusion | None = None,
    ) -> None:
        self.camera = camera
        self.detector = detector
        self.pose_estimator = pose_estimator
        self.tracker = tracker
        self.event_bus = event_bus
        self.station_id = station_id
        self.har_runtime = har_runtime
        self.object_detector = object_detector
        self.hand_extractor = hand_extractor or PoseBasedHandExtractor()
        self.interaction_associator = interaction_associator or HandObjectAssociator()
        self.interaction_state_machine = interaction_state_machine or InteractionStateMachine()
        self.multimodal_fusion = multimodal_fusion or DeterministicMultimodalFusion()

        self._is_running: bool = False
        self._loop_task: asyncio.Task[None] | None = None
        self._latest_observation: StructuredObservation | None = None
        self._fps_history: list[float] = []
        self._last_frame_ts: float = time.perf_counter()

        # Bounded operational metrics and health tracking
        self._frames_received: int = 0
        self._frames_processed: int = 0
        self._frames_failed: int = 0
        self._consecutive_failures: int = 0
        self._last_frame_index: int = 0
        self._last_observation_utc: datetime | None = None
        self._last_success_utc: datetime | None = None
        self._current_latency_ms: float = 0.0
        self._latency_history: deque[float] = deque(maxlen=30)
        self._max_latency_ms: float = 0.0
        self._pipeline_errors: int = 0
        self._last_error: str | None = None
        self._latest_jpeg_bytes: bytes | None = None

    @property
    def is_running(self) -> bool:
        """Return pipeline active running state."""
        return self._is_running

    @property
    def latest_jpeg_bytes(self) -> bytes | None:
        """Return raw encoded JPEG bytes of the most recent optical frame."""
        return self._latest_jpeg_bytes

    @property
    def latest_observation(self) -> StructuredObservation | None:
        """Return the most recently generated structured AI observation."""
        return self._latest_observation

    @property
    def frames_received(self) -> int:
        """Return total frames read from camera."""
        return self._frames_received

    @property
    def frames_processed(self) -> int:
        """Return total frames successfully processed."""
        return self._frames_processed

    @property
    def frames_failed(self) -> int:
        """Return total frames that encountered errors."""
        return self._frames_failed

    @property
    def consecutive_failures(self) -> int:
        """Return count of consecutive frame failures."""
        return self._consecutive_failures

    @property
    def last_frame_index(self) -> int:
        """Return index of latest processed frame."""
        return self._last_frame_index

    @property
    def last_observation_timestamp(self) -> datetime | None:
        """Return timestamp of latest generated observation."""
        return self._last_observation_utc

    @property
    def last_success_timestamp(self) -> datetime | None:
        """Return timestamp of latest successful pipeline execution."""
        return self._last_success_utc

    @property
    def current_processing_latency_ms(self) -> float:
        """Return latency of most recent frame execution."""
        return self._current_latency_ms

    @property
    def average_processing_latency_ms(self) -> float:
        """Return rolling average processing latency in milliseconds."""
        if not self._latency_history:
            return 0.0
        return float(sum(self._latency_history) / len(self._latency_history))

    @property
    def max_processing_latency_ms(self) -> float:
        """Return maximum observed processing latency in milliseconds."""
        return self._max_latency_ms

    @property
    def pipeline_errors(self) -> int:
        """Return total pipeline error count."""
        return self._pipeline_errors

    @property
    def last_error(self) -> str | None:
        """Return last encountered error message."""
        return self._last_error

    def get_health_report(self) -> SubsystemReport:
        """Produce structured subsystem health diagnostic report."""
        now = datetime.now(UTC)
        if not self._is_running:
            status = SubsystemStatus.OFFLINE
            err = "Pipeline coordinator is stopped"
        elif self._consecutive_failures >= 10:
            status = SubsystemStatus.ERROR
            err = f"Pipeline experiencing sustained failures: {self._last_error}"
        elif self._consecutive_failures > 0:
            status = SubsystemStatus.DEGRADED
            err = f"Pipeline transient failures ({self._consecutive_failures}): {self._last_error}"
        else:
            status = SubsystemStatus.HEALTHY
            err = None

        return SubsystemReport(
            subsystem_id="pipeline",
            status=status,
            timestamp=now,
            last_success=self._last_success_utc,
            latency_ms=self._current_latency_ms,
            metrics={
                "frames_received": self._frames_received,
                "frames_processed": self._frames_processed,
                "frames_failed": self._frames_failed,
                "consecutive_failures": self._consecutive_failures,
                "average_latency_ms": round(self.average_processing_latency_ms, 2),
                "max_latency_ms": round(self._max_latency_ms, 2),
                "pipeline_errors": self._pipeline_errors,
            },
            details={
                "last_frame_index": self._last_frame_index,
                "is_running": self._is_running,
            },
            error_message=err,
        )

    async def start(self) -> None:
        """Start the continuous asynchronous optical inference loop."""
        if self._is_running:
            return

        logger.info("Starting perception pipeline coordinator")
        try:
            await self.camera.initialize()
        except Exception as cam_err:
            self._last_error = str(cam_err)
            logger.warning("Camera initialization failed during pipeline startup", error=str(cam_err))
            await self.event_bus.publish(
                HealthChanged(
                    station_id=self.station_id,
                    subsystem="Camera",
                    status="OFFLINE",
                    metrics={"is_running": 0.0},
                    details=f"Camera initialization failed: {cam_err}",
                )
            )
            raise

        if self.har_runtime is not None:
            await self.har_runtime.initialize()
        self._is_running = True
        self._loop_task = asyncio.create_task(self._run_loop())

        await self.event_bus.publish(
            HealthChanged(
                station_id=self.station_id,
                subsystem="Pipeline",
                status="HEALTHY",
                metrics={"is_running": 1.0},
                details="Perception pipeline coordinator active",
            )
        )

    async def stop(self) -> None:
        """Gracefully halt inference loop and release hardware drivers."""
        self._is_running = False
        if self._loop_task:
            self._loop_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._loop_task
        await self.camera.shutdown()
        if self.har_runtime is not None:
            await self.har_runtime.shutdown()
        logger.info("Perception pipeline coordinator stopped")

        await self.event_bus.publish(
            HealthChanged(
                station_id=self.station_id,
                subsystem="Pipeline",
                status="OFFLINE",
                metrics={"is_running": 0.0},
                details="Perception pipeline coordinator halted",
            )
        )

    async def process_single_frame(self) -> StructuredObservation:
        """Execute one complete forward pass of the perception DAG on the next frame."""
        self._frames_received += 1
        FRAMES_RECEIVED_TOTAL.labels(station_id=self.station_id).inc()
        t_start = time.perf_counter()

        # Stage 1: Frame Acquisition
        t_cam_start = time.perf_counter()
        contract, frame_buffer = await self.camera.read_frame()
        t_cam_ms = (time.perf_counter() - t_cam_start) * 1000.0

        await self.event_bus.publish(
            FrameCaptured(
                station_id=self.station_id,
                camera_id=contract.camera_id,
                frame_index=contract.frame_index,
                width=contract.resolution.width,
                height=contract.resolution.height,
                pixel_format=contract.pixel_format,
                timestamp_sensor_ns=contract.timestamp_sensor_ns,
                latency_ms=t_cam_ms,
            )
        )

        # Encode optical frame to JPEG for live telemetry stream (optimized for HUD streaming)
        image_b64: str | None = None
        try:
            h, w = frame_buffer.shape[:2]
            if w > 640:
                scale = 640.0 / w
                stream_frame = cv2.resize(frame_buffer, (640, int(h * scale)), interpolation=cv2.INTER_AREA)
            else:
                stream_frame = frame_buffer
            success, enc_buf = cv2.imencode(".jpg", stream_frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
            if success:
                self._latest_jpeg_bytes = enc_buf.tobytes()
        except Exception as exc:
            logger.debug("Optical frame JPEG encode skipped", error=str(exc))

        # Stage 2: Primary Detection (Crew / Persons)
        t_det_start = time.perf_counter()
        try:
            det_result = await self.detector.detect(frame_buffer, contract.frame_index)
            t_det_ms = det_result.inference_latency_ms
            await self.event_bus.publish(
                DetectionCompleted(
                    station_id=self.station_id,
                    frame_index=contract.frame_index,
                    detection_count=len(det_result.detections),
                    classes_detected=[d.class_name for d in det_result.detections],
                    inference_time_ms=t_det_ms,
                )
            )
        except Exception as exc:
            logger.error(
                "Primary detection stage failed", frame=contract.frame_index, error=str(exc)
            )
            det_result = DetectionResult(
                frame_index=contract.frame_index,
                timestamp_sensor_ns=contract.timestamp_sensor_ns,
                detections=[],
                inference_latency_ms=0.0,
            )
            t_det_ms = (time.perf_counter() - t_det_start) * 1000.0

        # Stage 2b: Object Detection (Tools / Consumables / Chambers)
        t_obj_ms = 0.0
        obj_detections: list[DetectionTarget] = []
        if self.object_detector is not None:
            t_obj_start = time.perf_counter()
            try:
                obj_res = await self.object_detector.detect(frame_buffer, contract.frame_index)
                obj_detections = obj_res.detections
                t_obj_ms = obj_res.inference_latency_ms
            except Exception as exc:
                logger.error(
                    "Object detection stage failed", frame=contract.frame_index, error=str(exc)
                )
                t_obj_ms = (time.perf_counter() - t_obj_start) * 1000.0

        # Augment with spatial-chromatic detection of red and yellow boxes with person face masking & NMS
        try:
            h_f, w_f = frame_buffer.shape[:2]
            scale_box = 640.0 / max(h_f, w_f)
            small_f = cv2.resize(frame_buffer, (int(w_f * scale_box), int(h_f * scale_box)))
            hsv = cv2.cvtColor(small_f, cv2.COLOR_BGR2HSV)

            # Mask out head region of any detected person to prevent skin/face/lip false positives
            mask_ignore = np.zeros(small_f.shape[:2], dtype=np.uint8)
            for d in det_result.detections:
                if d.class_name == "person":
                    px_min = max(0, int(d.box.x_min * scale_box))
                    py_min = max(0, int(d.box.y_min * scale_box))
                    px_max = min(small_f.shape[1], int(d.box.x_max * scale_box))
                    # Upper 50% of person bounding box is head / face / neck
                    py_max = min(small_f.shape[0], int((d.box.y_min + (d.box.y_max - d.box.y_min) * 0.50) * scale_box))
                    cv2.rectangle(mask_ignore, (px_min, py_min), (px_max, py_max), 255, -1)

            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

            # Yellow mask (vivid yellow S>=135, V>=100)
            y_mask = cv2.inRange(hsv, (20, 135, 100), (32, 255, 255))
            y_mask = cv2.bitwise_and(y_mask, y_mask, mask=cv2.bitwise_not(mask_ignore))
            y_mask = cv2.morphologyEx(y_mask, cv2.MORPH_OPEN, kernel)
            y_mask = cv2.morphologyEx(y_mask, cv2.MORPH_CLOSE, kernel)

            # Red mask (vivid red S>=135, V>=100)
            r_mask1 = cv2.inRange(hsv, (0, 135, 100), (6, 255, 255))
            r_mask2 = cv2.inRange(hsv, (174, 135, 100), (180, 255, 255))
            r_mask = cv2.bitwise_or(r_mask1, r_mask2)
            r_mask = cv2.bitwise_and(r_mask, r_mask, mask=cv2.bitwise_not(mask_ignore))
            r_mask = cv2.morphologyEx(r_mask, cv2.MORPH_OPEN, kernel)
            r_mask = cv2.morphologyEx(r_mask, cv2.MORPH_CLOSE, kernel)

            box_candidates: list[dict[str, Any]] = []

            for mask, cls_name, cls_id in [(y_mask, "yellow_box", 101), (r_mask, "red_box", 102)]:
                cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for c in cnts:
                    area = cv2.contourArea(c)
                    # Filter out tiny noise and gigantic whole-frame background objects (max 12% frame)
                    if 800 <= area <= (small_f.shape[0] * small_f.shape[1] * 0.12):
                        bx, by, bw, bh = cv2.boundingRect(c)
                        # Box must not be anchored to ceiling / top wall border
                        if by <= 5:
                            continue
                        aspect = bw / float(bh)
                        fill_ratio = area / float(bw * bh)
                        # True experiment boxes have aspect ratio between 0.45 and 2.2 and solid rectangular fill
                        if 0.45 <= aspect <= 2.2 and fill_ratio >= 0.55:
                            box_candidates.append({
                                "class_name": cls_name,
                                "class_id": cls_id,
                                "area": area,
                                "confidence": min(0.95, max(0.70, fill_ratio)),
                                "box": BoundingBox2D(
                                    x_min=float(bx / scale_box),
                                    y_min=float(by / scale_box),
                                    x_max=float((bx + bw) / scale_box),
                                    y_max=float((by + bh) / scale_box),
                                ),
                            })

            # Non-Maximum Suppression (IoU <= 0.3) to prevent multiple overlapping duplicate boxes
            box_candidates.sort(key=lambda x: x["area"], reverse=True)
            kept_boxes: list[dict[str, Any]] = []
            for cand in box_candidates:
                b1 = cand["box"]
                overlap = False
                for k in kept_boxes:
                    b2 = k["box"]
                    xi1 = max(b1.x_min, b2.x_min)
                    yi1 = max(b1.y_min, b2.y_min)
                    xi2 = min(b1.x_max, b2.x_max)
                    yi2 = min(b1.y_max, b2.y_max)
                    inter = max(0.0, xi2 - xi1) * max(0.0, yi2 - yi1)
                    a1 = (b1.x_max - b1.x_min) * (b1.y_max - b1.y_min)
                    a2 = (b2.x_max - b2.x_min) * (b2.y_max - b2.y_min)
                    iou = inter / (a1 + a2 - inter + 1e-6)
                    if iou > 0.3:
                        overlap = True
                        break
                if not overlap:
                    kept_boxes.append(cand)
                    if len(kept_boxes) >= 4:
                        break

            for kb in kept_boxes:
                obj_detections.append(DetectionTarget(
                    class_id=kb["class_id"],
                    class_name=kb["class_name"],
                    confidence=kb["confidence"],
                    box=kb["box"],
                ))
        except Exception as exc:
            logger.debug("Box detection augmentation skipped", error=str(exc))

        # Combine detections for multi-class ByteTracking
        combined_detections = list(det_result.detections) + obj_detections
        combined_det_result = DetectionResult(
            frame_index=contract.frame_index,
            timestamp_sensor_ns=contract.timestamp_sensor_ns,
            detections=combined_detections,
            inference_latency_ms=t_det_ms + t_obj_ms,
        )

        # Stage 3: Multi-Object Multi-Class Tracking
        t_track_start = time.perf_counter()
        try:
            track_result = self.tracker.update(combined_det_result)
            t_track_ms = (time.perf_counter() - t_track_start) * 1000.0
        except Exception as exc:
            logger.error("Tracking stage failed", frame=contract.frame_index, error=str(exc))
            from orion_ai.tracking.schemas import TrackingResult

            track_result = TrackingResult(frame_index=contract.frame_index, active_tracks=[])
            t_track_ms = (time.perf_counter() - t_track_start) * 1000.0

        # Convert tracked objects into ObjectObservations (with fallback to raw object detections)
        object_observations = tracked_objects_to_observations(
            track_result.active_tracks,
            contract.frame_index,
            contract.timestamp_utc,
            contract.camera_id,
        )
        if not object_observations and obj_detections:
            for idx, od in enumerate(obj_detections):
                object_observations.append(
                    ObjectObservation(
                        object_id=f"det_{od.class_name}_{idx}",
                        class_name=od.class_name,
                        bbox=od.box,
                        confidence=od.confidence,
                        track_id=None,
                        frame_index=contract.frame_index,
                        timestamp=contract.timestamp_utc,
                        source_id=contract.camera_id,
                    )
                )

        # Stage 4: Pose Estimation (with error containment)
        t_pose_start = time.perf_counter()
        try:
            pose_result = await self.pose_estimator.estimate(frame_buffer, det_result)
            _associate_poses_with_tracks(pose_result.poses, track_result.active_tracks)
            t_pose_ms = pose_result.inference_time_ms
            await self.event_bus.publish(
                PoseCompleted(
                    station_id=self.station_id,
                    frame_index=contract.frame_index,
                    person_count=len(pose_result.poses),
                    topology="coco_17",
                    inference_time_ms=t_pose_ms,
                )
            )
        except Exception as exc:
            logger.error("Pose estimation stage failed", frame=contract.frame_index, error=str(exc))
            from orion_ai.pose.schemas import PoseEstimationResult

            pose_result = PoseEstimationResult(
                frame_index=contract.frame_index,
                poses=[],
                inference_time_ms=0.0,
            )
            t_pose_ms = (time.perf_counter() - t_pose_start) * 1000.0

        # Stage 4b: Hand Perception Extraction
        t_hand_start = time.perf_counter()
        hand_observations: list[HandObservation] = []
        try:
            hand_observations = self.hand_extractor.extract_hands(
                frame_buffer=frame_buffer,
                poses=pose_result.poses,
                tracks=track_result.active_tracks,
                frame_index=contract.frame_index,
                timestamp=contract.timestamp_utc,
                source_id=contract.camera_id,
            )
            t_hand_ms = (time.perf_counter() - t_hand_start) * 1000.0
        except Exception as exc:
            logger.error("Hand extraction stage failed", frame=contract.frame_index, error=str(exc))
            t_hand_ms = (time.perf_counter() - t_hand_start) * 1000.0

        # Stage 4c: Hand-Object Association & Interaction State Tracking
        t_int_start = time.perf_counter()
        interaction_observations: list[InteractionObservation] = []
        try:
            ref_diag = 1000.0
            if pose_result.poses and pose_result.poses[0].bbox:
                b = pose_result.poses[0].bbox
                ref_diag = max(50.0, (b.width ** 2 + b.height ** 2) ** 0.5)

            candidates = self.interaction_associator.associate(
                hands=hand_observations,
                objects=object_observations,
                reference_diagonal=ref_diag,
            )
            interaction_observations = self.interaction_state_machine.update(
                candidates=candidates,
                frame_index=contract.frame_index,
            )
            t_int_ms = (time.perf_counter() - t_int_start) * 1000.0
        except Exception as exc:
            logger.error("Interaction association stage failed", frame=contract.frame_index, error=str(exc))
            t_int_ms = (time.perf_counter() - t_int_start) * 1000.0

        # FPS History Calculation
        now_ts = time.perf_counter()
        instantaneous_fps = 1.0 / max(now_ts - self._last_frame_ts, 0.001)
        self._last_frame_ts = now_ts

        self._fps_history.append(instantaneous_fps)
        if len(self._fps_history) > FPS_HISTORY_WINDOW:
            self._fps_history.pop(0)
        avg_fps = float(sum(self._fps_history) / len(self._fps_history))

        # Stage 5: Temporal Human Activity Recognition (HAR) with fault containment
        t_har_start = time.perf_counter()
        har_results: list[ActivityRecognitionResult] = []
        t_har_ms = 0.0
        if self.har_runtime is not None:
            try:
                har_results, har_events = await self.har_runtime.process_frame_poses(
                    frame_index=contract.frame_index,
                    poses=pose_result.poses,
                    fps=round(avg_fps) if avg_fps > 0 else 30,
                )
                for event in har_events:
                    await self.event_bus.publish(event)
                t_har_ms = (time.perf_counter() - t_har_start) * 1000.0
            except Exception as exc:
                logger.error(
                    "Temporal HAR stage failed",
                    frame=contract.frame_index,
                    error=str(exc),
                )
                har_results = []
                t_har_ms = (time.perf_counter() - t_har_start) * 1000.0

        # Stage 5b: Multimodal Evidence Fusion
        t_fuse_start = time.perf_counter()
        multimodal_evidence: MultimodalActivityEvidence | None = None
        t_fuse_ms = 0.0
        if har_results:
            try:
                top_har = har_results[0]
                pred_act = top_har.top_prediction.activity_name if top_har.top_prediction else "idle"
                pred_conf = top_har.top_prediction.confidence if top_har.top_prediction else 0.0
                pid = top_har.track_id
                person_pose = next((p for p in pose_result.poses if p.person_id == pid), None)
                person_track = next((t for t in track_result.active_tracks if t.track_id == pid), None)

                multimodal_evidence = self.multimodal_fusion.fuse(
                    predicted_activity=pred_act,
                    activity_confidence=pred_conf,
                    person_track_id=pid,
                    pose=person_pose,
                    track=person_track,
                    hands=hand_observations,
                    objects=object_observations,
                    interactions=interaction_observations,
                    window_start=contract.frame_index,
                    window_end=contract.frame_index,
                    source_id=contract.camera_id,
                )
                t_fuse_ms = (time.perf_counter() - t_fuse_start) * 1000.0

                # Publish MultimodalEvidenceUpdated event
                await self.event_bus.publish(
                    MultimodalEvidenceUpdated(
                        station_id=self.station_id,
                        activity=multimodal_evidence.activity,
                        person_track_id=multimodal_evidence.person_track_id,
                        evidence_state=multimodal_evidence.evidence_state.value,
                        evidence_quality_level=multimodal_evidence.evidence_quality.overall.value,
                        confidence=multimodal_evidence.confidence,
                        uncertainty_status=multimodal_evidence.uncertainty_status,
                    )
                )
            except Exception as exc:
                logger.error(
                    "Multimodal fusion stage failed",
                    frame=contract.frame_index,
                    error=str(exc),
                )
                t_fuse_ms = (time.perf_counter() - t_fuse_start) * 1000.0

        # Stage 6: Telemetry Metrics Calculation
        t_total_ms = (time.perf_counter() - t_start) * 1000.0

        # Update Prometheus latency instruments
        INFERENCE_LATENCY_MS.labels(stage="camera").set(t_cam_ms)
        INFERENCE_LATENCY_MS.labels(stage="detection").set(t_det_ms)
        INFERENCE_LATENCY_MS.labels(stage="pose").set(t_pose_ms)
        INFERENCE_LATENCY_MS.labels(stage="tracking").set(t_track_ms)
        INFERENCE_LATENCY_MS.labels(stage="har").set(t_har_ms)
        INFERENCE_LATENCY_MS.labels(stage="total").set(t_total_ms)

        self._current_latency_ms = t_total_ms
        self._latency_history.append(t_total_ms)
        self._max_latency_ms = max(self._max_latency_ms, t_total_ms)
        INFERENCE_LATENCY_AVG_MS.labels(station_id=self.station_id).set(self.average_processing_latency_ms)

        self._last_frame_index = contract.frame_index
        self._last_observation_utc = contract.timestamp_utc

        metrics = PipelineMetrics(
            camera_latency_ms=t_cam_ms,
            detection_latency_ms=t_det_ms,
            object_latency_ms=t_obj_ms,
            pose_latency_ms=t_pose_ms,
            hand_latency_ms=t_hand_ms,
            tracking_latency_ms=t_track_ms,
            har_latency_ms=t_har_ms,
            interaction_latency_ms=t_int_ms,
            fusion_latency_ms=t_fuse_ms,
            pipeline_latency_ms=t_total_ms,
            fps=round(avg_fps, 1),
            dropped_frames_total=getattr(self.camera, "dropped_frames", 0),
        )

        observation = StructuredObservation(
            station_id=self.station_id,
            frame_index=contract.frame_index,
            timestamp_utc=contract.timestamp_utc,
            source_id=contract.camera_id,
            width=contract.resolution.width,
            height=contract.resolution.height,
            detections=combined_detections,
            poses=pose_result.poses,
            tracks=track_result.active_tracks,
            hand_observations=hand_observations,
            object_observations=object_observations,
            interaction_observations=interaction_observations,
            activities=har_results,
            top_activity=har_results[0].top_prediction if har_results else None,
            multimodal_evidence=multimodal_evidence,
            metrics=metrics,
            pipeline_status="NOMINAL",
            image_jpeg=image_b64,
        )

        self._latest_observation = observation

        await self.event_bus.publish(
            ObservationCaptured(
                station_id=self.station_id,
                observation=observation,
            )
        )
        OBSERVATIONS_PUBLISHED_TOTAL.labels(station_id=self.station_id).inc()

        return observation

    async def switch_camera_source(self, source: str | int) -> None:
        """Dynamically switch optical input source (e.g. webcam vs sample replay video)."""
        logger.info("Switching optical camera source", new_source=str(source))
        was_running = self._is_running
        if was_running:
            self._is_running = False
            if self._loop_task:
                self._loop_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._loop_task
        await self.camera.shutdown()

        from orion_ai.camera.opencv_driver import OpenCVCameraDriver

        is_fallback = False
        if isinstance(source, str) and not source.isdigit():
            is_fallback = "sample_replay" in source

        self.camera = OpenCVCameraDriver(
            source=source,
            camera_id=f"cam_{self.station_id.lower()}",
            target_fps=30,
            width=640,
            height=480,
            loop=True,
            is_replay_fallback=is_fallback,
        )
        await self.camera.initialize()
        if was_running:
            self._is_running = True
            self._loop_task = asyncio.create_task(self._run_loop())
        logger.info("Optical camera source switched successfully", source=str(source))

    async def _run_loop(self) -> None:
        """Continuous pipeline loop with failure tolerance, bounded backoff, and health emission."""
        while self._is_running:
            try:
                await self.process_single_frame()
                self._frames_processed += 1
                if self._consecutive_failures > 0:
                    logger.info(
                        "Pipeline recovered after transient failures",
                        consecutive_failures=self._consecutive_failures,
                    )
                    self._consecutive_failures = 0
                    await self.event_bus.publish(
                        HealthChanged(
                            station_id=self.station_id,
                            subsystem="Pipeline",
                            status="HEALTHY",
                            details="Pipeline recovered nominal execution",
                        )
                    )
                self._last_success_utc = datetime.now(UTC)
                FRAMES_PROCESSED_TOTAL.labels(station_id=self.station_id).inc()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._frames_failed += 1
                self._consecutive_failures += 1
                self._pipeline_errors += 1
                self._last_error = str(exc)
                FRAMES_FAILED_TOTAL.labels(station_id=self.station_id).inc()
                PIPELINE_ERRORS_TOTAL.labels(stage="pipeline").inc()
                logger.error(
                    "Unhandled pipeline frame failure",
                    consecutive_failures=self._consecutive_failures,
                    error=str(exc),
                )
                if self._consecutive_failures == 3:
                    await self.event_bus.publish(
                        HealthChanged(
                            station_id=self.station_id,
                            subsystem="Pipeline",
                            status="DEGRADED",
                            details=f"Consecutive frame failures: {self._consecutive_failures}",
                        )
                    )
                elif self._consecutive_failures >= 10:
                    await self.event_bus.publish(
                        HealthChanged(
                            station_id=self.station_id,
                            subsystem="Pipeline",
                            status="ERROR",
                            details=f"Excessive consecutive failures: {self._consecutive_failures}",
                        )
                    )
                # Bounded backoff: 0.05s up to 1.0s max
                backoff = min(1.0, 0.05 * (2 ** min(self._consecutive_failures, 4)))
                await asyncio.sleep(backoff)


