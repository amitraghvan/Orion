"""ByteTrack-style multi-object tracking algorithm for ORION BAS AI Copilot."""

import time
from dataclasses import dataclass

from orion.core.logger import get_logger
from orion_ai.detection.schemas import BoundingBox2D, DetectionResult, DetectionTarget
from orion_ai.geometry.iou import compute_bbox_iou
from orion_ai.tracking.interfaces import TrackerInterface
from orion_ai.tracking.schemas import TrackedObject, TrackingResult, TrackState

logger = get_logger("orion_ai.tracking.bytetrack")


LOW_CONF_THRESHOLD: float = 0.1


@dataclass
class _Tracklet:
    track_id: int
    class_id: int
    class_name: str
    box: BoundingBox2D
    confidence: float
    state: TrackState
    age_frames: int
    lost_frames: int
    prev_centroid: tuple[float, float]
    velocity: tuple[float, float]
    last_timestamp_s: float


class ByteTracker(TrackerInterface):
    """High-speed IoU and two-stage association tracker inspired by ByteTrack."""

    def __init__(
        self,
        high_score_thresh: float = 0.5,
        match_thresh: float = 0.3,
        max_lost_frames: int = 30,
    ) -> None:
        self.high_score_thresh = high_score_thresh
        self.match_thresh = match_thresh
        self.max_lost_frames = max_lost_frames

        self._next_id: int = 1
        self._tracks: dict[int, _Tracklet] = {}

    def reset(self) -> None:
        """Purge all active tracklets and reset track ID counter."""
        self._tracks.clear()
        self._next_id = 1
        logger.info("ByteTracker reset")

    def update(self, detections: DetectionResult) -> TrackingResult:
        """Associate detections with existing tracks across consecutive frames."""
        now_s = time.time()

        # Partition detections into high and low confidence groups
        det_targets = detections.detections
        high_dets: list[DetectionTarget] = []
        low_dets: list[DetectionTarget] = []

        for det in det_targets:
            if det.confidence >= self.high_score_thresh:
                high_dets.append(det)
            elif det.confidence >= LOW_CONF_THRESHOLD:
                low_dets.append(det)

        active_track_ids = [
            tid
            for tid, trk in self._tracks.items()
            if trk.state in (TrackState.TRACKED, TrackState.NEW)
        ]

        matched_tracks: set[int] = set()
        matched_dets: set[int] = set()

        # Pass 1: Match high-confidence detections with active tracks
        for d_idx, det in enumerate(high_dets):
            best_iou = 0.0
            best_tid: int | None = None
            for tid in active_track_ids:
                if tid in matched_tracks:
                    continue
                trk = self._tracks[tid]
                # Enforce strict class matching: cannot match person to chair or bottle
                if det.class_id != trk.class_id:
                    continue
                iou = compute_bbox_iou(det.box, trk.box)
                if iou > best_iou and iou >= self.match_thresh:
                    best_iou = iou
                    best_tid = tid

            if best_tid is not None:
                matched_tracks.add(best_tid)
                matched_dets.add(d_idx)
                self._update_track(best_tid, det, now_s)
                det.track_id = best_tid

        # Pass 2: Match unmatched tracks with low-confidence detections
        unmatched_active = [tid for tid in active_track_ids if tid not in matched_tracks]
        for tid in unmatched_active:
            trk = self._tracks[tid]
            best_iou = 0.0
            best_d_idx: int | None = None
            for d_idx, det in enumerate(low_dets):
                if d_idx in matched_dets:
                    continue
                # Enforce strict class matching
                if det.class_id != trk.class_id:
                    continue
                iou = compute_bbox_iou(det.box, trk.box)
                if iou > best_iou and iou >= self.match_thresh:
                    best_iou = iou
                    best_d_idx = d_idx

            if best_d_idx is not None:
                matched_tracks.add(tid)
                matched_dets.add(best_d_idx)
                det = low_dets[best_d_idx]
                self._update_track(tid, det, now_s)
                det.track_id = tid

        # Pass 3: Create new tracks for unmatched high-confidence detections
        new_track_ids: set[int] = set()
        for d_idx, det in enumerate(high_dets):
            if d_idx not in matched_dets:
                tid = self._create_track(det, now_s)
                det.track_id = tid
                new_track_ids.add(tid)

        # Pass 4: Age and remove stale tracks
        lost_ids: list[int] = []
        for tid in list(self._tracks.keys()):
            if tid in new_track_ids:
                continue
            if tid not in matched_tracks:
                trk = self._tracks[tid]
                trk.lost_frames += 1
                trk.state = TrackState.LOST
                if trk.lost_frames > self.max_lost_frames:
                    lost_ids.append(tid)
                    del self._tracks[tid]

        # Assemble results
        active_tracked: list[TrackedObject] = []
        for _tid, trk in self._tracks.items():
            active_tracked.append(
                TrackedObject(
                    track_id=trk.track_id,
                    class_id=trk.class_id,
                    class_name=trk.class_name,
                    box=trk.box,
                    velocity_px_per_sec=trk.velocity,
                    confidence=trk.confidence,
                    state=trk.state,
                    age_frames=trk.age_frames,
                )
            )

        return TrackingResult(
            frame_index=detections.frame_index,
            active_tracks=active_tracked,
            lost_tracks=lost_ids,
        )

    def get_person_tracks(self, person_class_id: int = 0) -> list[TrackedObject]:
        """Return all active tracks belonging specifically to the person class."""
        return [
            TrackedObject(
                track_id=trk.track_id,
                class_id=trk.class_id,
                class_name=trk.class_name,
                box=trk.box,
                velocity_px_per_sec=trk.velocity,
                confidence=trk.confidence,
                state=trk.state,
                age_frames=trk.age_frames,
            )
            for trk in self._tracks.values()
            if trk.class_id == person_class_id and trk.state in (TrackState.TRACKED, TrackState.NEW)
        ]

    def _create_track(self, det: DetectionTarget, now_s: float) -> int:
        """Instantiate a new tracklet from an unassociated high-confidence detection."""
        tid = self._next_id
        self._next_id += 1
        cx = (det.box.x_min + det.box.x_max) / 2.0
        cy = (det.box.y_min + det.box.y_max) / 2.0

        self._tracks[tid] = _Tracklet(
            track_id=tid,
            class_id=det.class_id,
            class_name=det.class_name,
            box=det.box,
            confidence=det.confidence,
            state=TrackState.NEW,
            age_frames=1,
            lost_frames=0,
            prev_centroid=(cx, cy),
            velocity=(0.0, 0.0),
            last_timestamp_s=now_s,
        )
        return tid

    def _update_track(self, tid: int, det: DetectionTarget, now_s: float) -> None:
        """Update existing tracklet state and compute velocity vector."""
        trk = self._tracks[tid]
        cx = (det.box.x_min + det.box.x_max) / 2.0
        cy = (det.box.y_min + det.box.y_max) / 2.0
        dt = max(now_s - trk.last_timestamp_s, 0.001)

        vx = (cx - trk.prev_centroid[0]) / dt
        vy = (cy - trk.prev_centroid[1]) / dt

        trk.box = det.box
        trk.confidence = det.confidence
        trk.class_id = det.class_id
        trk.class_name = det.class_name
        trk.state = TrackState.TRACKED
        trk.age_frames += 1
        trk.lost_frames = 0
        trk.prev_centroid = (cx, cy)
        trk.velocity = (vx, vy)
        trk.last_timestamp_s = now_s
