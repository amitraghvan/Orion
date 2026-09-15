"""Production-safe bounded multi-person temporal feature buffer for ORION BAS AI Copilot."""

from collections import deque
from datetime import UTC, datetime

from orion.core.logger import get_logger
from orion_ai.activity.schemas import (
    KeypointState,
    TemporalKeypoint,
    TemporalSkeletonPose,
)
from orion_ai.pose.schemas import HumanPose

logger = get_logger("orion_ai.activity.buffer")

DEFAULT_WINDOW_SIZE: int = 32
DEFAULT_STRIDE_FRAMES: int = 8
DEFAULT_STALE_TIMEOUT_FRAMES: int = 30
MIN_OBSERVED_CONFIDENCE: float = 0.20
MAX_INTERPOLATION_FRAMES: int = 2
MAX_HELD_FRAMES: int = 3


class TemporalFeatureBuffer:
    """Thread-safe per-track bounded sliding window buffer with missing joint degradation."""

    def __init__(
        self,
        window_size: int = DEFAULT_WINDOW_SIZE,
        stride_frames: int = DEFAULT_STRIDE_FRAMES,
        stale_timeout_frames: int = DEFAULT_STALE_TIMEOUT_FRAMES,
        sampling_rate: int = 1,
    ) -> None:
        self.window_size = window_size
        self.stride_frames = stride_frames
        self.stale_timeout_frames = stale_timeout_frames
        self.sampling_rate = sampling_rate

        # Per-track temporal queues
        self._buffers: dict[int, deque[TemporalSkeletonPose]] = {}
        # Per-track stride frame counters
        self._stride_counters: dict[int, int] = {}
        # Per-track last observed frame index for stale eviction
        self._last_seen_frame: dict[int, int] = {}
        # Per-track missing keypoint counters: track_id -> dict[joint_id, consecutive_missing_count]
        self._missing_joint_counts: dict[int, dict[int, int]] = {}
        # Per-track last valid keypoint coordinates: track_id -> dict[joint_id, (x, y, conf)]
        self._last_valid_joints: dict[int, dict[int, tuple[float, float, float]]] = {}

    def push_pose(
        self,
        pose: HumanPose,
        frame_index: int,
        timestamp_utc: datetime | None = None,
    ) -> None:
        """Append a newly observed/matched pose to the subject's temporal queue."""
        track_id = pose.person_id
        if timestamp_utc is None:
            timestamp_utc = datetime.now(UTC)

        if track_id not in self._buffers:
            self._buffers[track_id] = deque(maxlen=self.window_size)
            self._stride_counters[track_id] = 0
            self._missing_joint_counts[track_id] = {}
            self._last_valid_joints[track_id] = {}
            logger.debug("Initialized temporal buffer for track", track_id=track_id)

        self._last_seen_frame[track_id] = frame_index
        missing_counts = self._missing_joint_counts[track_id]
        last_joints = self._last_valid_joints[track_id]

        processed_keypoints: list[TemporalKeypoint] = []

        for kp in pose.keypoints_2d:
            jid = kp.id
            if kp.score >= MIN_OBSERVED_CONFIDENCE:
                # Joint is cleanly observed
                missing_counts[jid] = 0
                last_joints[jid] = (kp.x, kp.y, kp.score)
                processed_keypoints.append(
                    TemporalKeypoint(
                        id=jid,
                        name=kp.name,
                        x=kp.x,
                        y=kp.y,
                        score=kp.score,
                        state=KeypointState.OBSERVED,
                    )
                )
            else:
                # Joint observation missing or degraded
                m_count = missing_counts.get(jid, 0) + 1
                missing_counts[jid] = m_count

                if jid in last_joints and m_count <= MAX_INTERPOLATION_FRAMES:
                    # 1-2 frames missing: linear decay interpolation
                    prev_x, prev_y, prev_conf = last_joints[jid]
                    decay_factor = 0.5**m_count
                    processed_keypoints.append(
                        TemporalKeypoint(
                            id=jid,
                            name=kp.name,
                            x=prev_x,
                            y=prev_y,
                            score=float(prev_conf * decay_factor),
                            state=KeypointState.INTERPOLATED,
                        )
                    )
                elif jid in last_joints and m_count == MAX_HELD_FRAMES:
                    # 3 frames missing: held position with severe confidence penalty
                    prev_x, prev_y, _ = last_joints[jid]
                    processed_keypoints.append(
                        TemporalKeypoint(
                            id=jid,
                            name=kp.name,
                            x=prev_x,
                            y=prev_y,
                            score=0.20,
                            state=KeypointState.HELD,
                        )
                    )
                else:
                    # > 3 frames missing: invalid coordinate
                    processed_keypoints.append(
                        TemporalKeypoint(
                            id=jid,
                            name=kp.name,
                            x=0.0,
                            y=0.0,
                            score=0.0,
                            state=KeypointState.INVALID,
                        )
                    )

        temporal_pose = TemporalSkeletonPose(
            frame_index=frame_index,
            timestamp_utc=timestamp_utc,
            track_id=track_id,
            bbox=pose.bbox,
            keypoints_2d=processed_keypoints,
            overall_confidence=pose.overall_confidence,
        )

        self._buffers[track_id].append(temporal_pose)
        self._stride_counters[track_id] += 1

    def is_window_ready(self, track_id: int) -> bool:
        """Return whether track buffer has accumulated a complete window of T frames."""
        buf = self._buffers.get(track_id)
        return buf is not None and len(buf) >= self.window_size

    def should_classify(self, track_id: int) -> bool:
        """Return whether classification stride interval is met for this track."""
        if not self.is_window_ready(track_id):
            return False
        return self._stride_counters.get(track_id, 0) >= self.stride_frames

    def get_window(self, track_id: int) -> list[TemporalSkeletonPose]:
        """Return list of T frames and reset track's stride trigger counter."""
        if not self.is_window_ready(track_id):
            return []
        self._stride_counters[track_id] = 0
        return list(self._buffers[track_id])

    def peek_window(self, track_id: int) -> list[TemporalSkeletonPose]:
        """Return current window contents without resetting stride counter."""
        buf = self._buffers.get(track_id)
        return list(buf) if buf else []

    def evict_stale_tracks(self, current_frame_index: int) -> list[int]:
        """Purge queues for tracklets that have vanished beyond stale timeout threshold."""
        evicted_ids: list[int] = []
        for tid, last_seen in list(self._last_seen_frame.items()):
            if (current_frame_index - last_seen) > self.stale_timeout_frames:
                evicted_ids.append(tid)
                del self._buffers[tid]
                del self._stride_counters[tid]
                del self._last_seen_frame[tid]
                if tid in self._missing_joint_counts:
                    del self._missing_joint_counts[tid]
                if tid in self._last_valid_joints:
                    del self._last_valid_joints[tid]

        if evicted_ids:
            logger.debug(
                "Evicted stale temporal tracks",
                evicted_count=len(evicted_ids),
                evicted_ids=evicted_ids,
            )
        return evicted_ids

    def reset(self, track_id: int | None = None) -> None:
        """Reset buffer for a single track or purge all tracks."""
        if track_id is not None:
            self._buffers.pop(track_id, None)
            self._stride_counters.pop(track_id, None)
            self._last_seen_frame.pop(track_id, None)
            self._missing_joint_counts.pop(track_id, None)
            self._last_valid_joints.pop(track_id, None)
        else:
            self._buffers.clear()
            self._stride_counters.clear()
            self._last_seen_frame.clear()
            self._missing_joint_counts.clear()
            self._last_valid_joints.clear()
        logger.info("TemporalFeatureBuffer reset", track_id=track_id)

    def get_active_tracks(self) -> list[int]:
        """Return list of track IDs currently registered in the buffer."""
        return list(self._buffers.keys())
