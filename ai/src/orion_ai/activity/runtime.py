import logging
from datetime import UTC, datetime

from orion.events.schemas import ActivityRecognized
from orion.health.interfaces import SubsystemReport, SubsystemStatus
from orion_ai.activity.buffer import TemporalFeatureBuffer
from orion_ai.activity.configs import ActivityConfig
from orion_ai.activity.schemas import (
    ActivityPrediction,
    ActivityRecognitionResult,
    ActivityWindow,
    KeypointState,
    UncertaintyStatus,
)
from orion_ai.activity.smoothing import (
    ActivityEventTranslator,
    TemporalPredictionSmoother,
    UncertaintyEvaluator,
)
from orion_ai.activity.stgcn_classifier import STGCNActivityClassifier
from orion_ai.pose.schemas import HumanPose

logger = logging.getLogger(__name__)

DEGRADED_INVALID_RATIO_THRESHOLD: float = 0.35


class TemporalHARRuntime:
    """Encapsulates sliding-window buffering, ST-GCN inference, smoothing, uncertainty, and event translation."""

    def __init__(
        self,
        config: ActivityConfig | None = None,
        model_path: str = "models/weights/stgcn_har_v1.pt",
        device: str = "cpu",
        station_id: str = "BAS-NODE-01",
    ) -> None:
        self.config = config or ActivityConfig(
            model_id="stgcn_har_v1",
            window_size_frames=32,
            stride_frames=8,
            confidence_threshold=0.5,
        )
        self.model_path = model_path
        self.station_id = station_id

        self.buffer = TemporalFeatureBuffer(
            window_size=self.config.window_size_frames,
            stride_frames=self.config.stride_frames,
            stale_timeout_frames=30,
        )
        self.classifier = STGCNActivityClassifier(
            device=device,
            confidence_threshold=self.config.confidence_threshold,
        )
        self.smoother = TemporalPredictionSmoother(window_size=5)
        self.evaluator = UncertaintyEvaluator(
            entropy_threshold=1.4,
            confidence_threshold=self.config.confidence_threshold,
        )
        self.translator = ActivityEventTranslator(rate_limit_frames=4)

        self._latest_track_results: dict[int, ActivityRecognitionResult] = {}
        self._is_initialized = False
        self._inference_count: int = 0
        self._last_inference_utc: datetime | None = None
        self._last_latency_ms: float = 0.0
        self._last_error: str | None = None

    async def initialize(self) -> None:
        """Initialize and warm up ST-GCN neural network weights."""
        if self._is_initialized:
            return
        try:
            await self.classifier.load(self.model_path)
            self._is_initialized = True
            self._last_error = None
            logger.info("TemporalHARRuntime initialized with model %s", self.model_path)
        except Exception as exc:
            self._is_initialized = False
            self._last_error = str(exc)
            raise

    async def process_frame_poses(
        self,
        frame_index: int,
        poses: list[HumanPose],
        fps: int = 30,
    ) -> tuple[list[ActivityRecognitionResult], list[ActivityRecognized]]:
        """Process incoming 2D poses from optical pipeline, update temporal buffers, and run HAR on stride triggers.

        Returns:
            (active_track_results, events_to_emit)
        """
        if not self._is_initialized:
            await self.initialize()

        events_to_emit: list[ActivityRecognized] = []

        # Step 1: Push observed/associated poses into temporal buffer
        for pose in poses:
            self.buffer.push_pose(pose, frame_index=frame_index)

        # Step 2: Handle stale tracks that vanished
        stale_track_ids = self.buffer.evict_stale_tracks(frame_index)
        for tid in stale_track_ids:
            self.smoother.evict_track(tid)
            self._latest_track_results.pop(tid, None)
            end_info = self.translator.end_track(tid)
            if end_info is not None:
                last_act, end_phase = end_info
                events_to_emit.append(
                    ActivityRecognized(
                        station_id=self.station_id,
                        track_id=tid,
                        frame_index=frame_index,
                        window_start_frame=max(0, frame_index - self.config.window_size_frames),
                        window_end_frame=frame_index,
                        activity_label=last_act,
                        phase=end_phase.value,
                        confidence=0.0,
                        uncertainty_status=UncertaintyStatus.NOMINAL.value,
                        is_anomaly=False,
                        model_version=self.classifier.version,
                        evidence_metadata={"event": "track_lost", "evicted": True},
                    )
                )

        # Step 3: Check stride triggers for each active track
        for tid in self.buffer.get_active_tracks():
            if self.buffer.should_classify(tid):
                window_poses = self.buffer.get_window(tid)
                if not window_poses:
                    continue

                # Check keypoint reliability across the window
                total_kpts = len(window_poses) * 17
                invalid_kpts = sum(
                    1
                    for p in window_poses
                    for kp in p.keypoints_2d
                    if kp.state == KeypointState.INVALID
                )
                is_degraded = (invalid_kpts / max(total_kpts, 1)) > DEGRADED_INVALID_RATIO_THRESHOLD

                window_meta = ActivityWindow(
                    start_frame=window_poses[0].frame_index,
                    end_frame=window_poses[-1].frame_index,
                    fps=fps,
                    duration_seconds=len(window_poses) / max(fps, 1),
                    stride=self.config.stride_frames,
                    track_id=tid,
                )

                raw_result = await self.classifier.classify_window(
                    window_poses,
                    window=window_meta,
                )
                self._inference_count += 1
                self._last_inference_utc = datetime.now(UTC)
                self._last_latency_ms = raw_result.latency_ms
                self._last_error = None

                # Smooth class probabilities across consecutive windows
                smoothed_probs = self.smoother.smooth(
                    tid,
                    raw_result.top_prediction.probabilities,
                )

                # Evaluate uncertainty status
                status, entropy = self.evaluator.evaluate(
                    smoothed_probs,
                    is_degraded=is_degraded,
                    has_track=True,
                )

                # Determine top smoothed class and confidence
                top_class = max(smoothed_probs, key=smoothed_probs.get)  # type: ignore[arg-type]
                top_conf = smoothed_probs[top_class]

                # Translate activity lifecycle phase (START, UPDATE, CHANGE)
                is_nominal = status == UncertaintyStatus.NOMINAL
                phase, should_emit = self.translator.translate(
                    tid,
                    top_class,
                    frame_index=frame_index,
                )

                # Build final prediction and result
                prediction = ActivityPrediction(
                    activity_name=top_class,
                    phase=phase,
                    confidence=top_conf,
                    probabilities=smoothed_probs,
                    uncertainty_status=status,
                    is_nominal=is_nominal,
                    model_version=self.classifier.version,
                )

                candidates = [
                    ActivityPrediction(
                        activity_name=cls,
                        confidence=float(prob),
                        probabilities={},
                        uncertainty_status=status,
                        is_nominal=is_nominal,
                        model_version=self.classifier.version,
                    )
                    for cls, prob in sorted(
                        smoothed_probs.items(), key=lambda x: x[1], reverse=True
                    )
                ]

                result = ActivityRecognitionResult(
                    track_id=tid,
                    window=window_meta,
                    top_prediction=prediction,
                    candidates=candidates,
                    uncertainty_status=status,
                    latency_ms=raw_result.latency_ms,
                )

                self._latest_track_results[tid] = result

                if should_emit:
                    events_to_emit.append(
                        ActivityRecognized(
                            station_id=self.station_id,
                            track_id=tid,
                            frame_index=frame_index,
                            window_start_frame=window_meta.start_frame,
                            window_end_frame=window_meta.end_frame,
                            activity_label=top_class,
                            phase=phase.value,
                            confidence=top_conf,
                            uncertainty_status=status.value,
                            is_anomaly=False,
                            model_version=self.classifier.version,
                            evidence_metadata={
                                "entropy": entropy,
                                "is_degraded": is_degraded,
                                "latency_ms": raw_result.latency_ms,
                            },
                        )
                    )

        return list(self._latest_track_results.values()), events_to_emit

    async def shutdown(self) -> None:
        """Release neural network resources and clear buffers."""
        await self.classifier.unload()
        self.buffer.reset()
        self.smoother.clear()
        self.translator.clear()
        self._latest_track_results.clear()
        self._is_initialized = False
        logger.info("TemporalHARRuntime shutdown complete")

    def get_health_report(self) -> SubsystemReport:
        """Return standardized subsystem health diagnostic report."""
        now = datetime.now(UTC)
        if not self._is_initialized:
            status = SubsystemStatus.OFFLINE
            err = self._last_error or "ST-GCN model runtime not initialized"
        elif self._last_error:
            status = SubsystemStatus.DEGRADED
            err = f"Temporal HAR processing issue: {self._last_error}"
        else:
            status = SubsystemStatus.HEALTHY
            err = None

        return SubsystemReport(
            subsystem_id="har_model",
            status=status,
            timestamp=now,
            last_success=self._last_inference_utc,
            latency_ms=self._last_latency_ms,
            metrics={
                "inferences_total": self._inference_count,
                "is_initialized": self._is_initialized,
                "window_size": self.config.window_size_frames,
                "stride_frames": self.config.stride_frames,
            },
            details={
                "model_id": self.config.model_id,
                "optional": True,
            },
            error_message=err,
        )
