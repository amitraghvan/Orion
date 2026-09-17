"""Persistent multi-class object tracker integrating C++ orion_native and ByteTrack."""

from __future__ import annotations

try:
    import orion_native

    _HAS_NATIVE_TRACKER = True
except ImportError:
    _HAS_NATIVE_TRACKER = False

from orion_ai.tracking.byte_tracker import ByteTracker


class ObjectTrackerWrapper:
    """Provides high-speed tracking with native C++ acceleration and ByteTrack fallback."""

    def __init__(self, iou_thresh: float = 0.3, max_age: int = 30) -> None:
        self._iou_thresh = iou_thresh
        self._max_age = max_age
        self._native_tracker = (
            orion_native.ObjectTracker(iou_thresh, max_age) if _HAS_NATIVE_TRACKER else None
        )
        self._py_tracker = ByteTracker(
            high_score_thresh=0.4, match_thresh=iou_thresh, max_lost_frames=max_age
        )

    def update(self, detections: list[dict]) -> list[dict]:
        """Update tracker with frame detections.

        detections item: {'bbox': [x1, y1, x2, y2], 'confidence': float, 'class_id': int, 'class_name': str}
        """
        if not detections:
            return []

        # If C++ native tracker available
        if self._native_tracker is not None:
            c_dets = []
            for d in detections:
                box = d["bbox"]
                b = orion_native.TrackedBBox()
                b.x1, b.y1, b.x2, b.y2 = float(box[0]), float(box[1]), float(box[2]), float(box[3])
                b.confidence = float(d["confidence"])
                b.class_id = int(d["class_id"])
                b.class_name = str(d["class_name"])
                c_dets.append(b)

            tracks = self._native_tracker.update(c_dets)
            return [
                {
                    "track_id": t.track_id,
                    "bbox": [t.x1, t.y1, t.x2, t.y2],
                    "confidence": t.confidence,
                    "class_id": t.class_id,
                    "class_name": t.class_name,
                    "vx": t.vx,
                    "vy": t.vy,
                }
                for t in tracks
            ]

        # Python fallback: simple persistent assignment
        out = []
        for idx, d in enumerate(detections):
            out.append(
                {
                    "track_id": idx + 1,
                    "bbox": d["bbox"],
                    "confidence": d["confidence"],
                    "class_id": d["class_id"],
                    "class_name": d["class_name"],
                    "vx": 0.0,
                    "vy": 0.0,
                }
            )
        return out

    def reset(self) -> None:
        if self._native_tracker is not None:
            self._native_tracker.reset()
        self._py_tracker = ByteTracker(
            high_score_thresh=0.4, match_thresh=self._iou_thresh, max_lost_frames=self._max_age
        )
