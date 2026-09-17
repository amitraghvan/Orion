"""Pose estimation wrapper extracting 17 COCO keypoints and wrist projections."""

from __future__ import annotations

import numpy as np

# COCO keypoint names
COCO_KEYPOINTS = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle"
]

# Standard COCO skeletal bone connections
COCO_BONES = [
    (15, 13), (13, 11), (16, 14), (14, 12), (11, 12),
    (5, 11), (6, 12), (5, 6), (5, 7), (6, 8),
    (7, 9), (8, 10), (1, 2), (0, 1), (0, 2),
    (1, 3), (2, 4), (3, 5), (4, 6),
]


class PoseEstimatorWrapper:
    """Processes frames with YOLO pose model to extract human skeletons."""

    def __init__(self, min_confidence: float = 0.25) -> None:
        self.min_confidence = min_confidence

    def estimate(self, model_backend: Any, frame_bgr: np.ndarray) -> list[dict]:
        """Estimate 2D poses from frame.

        Returns list of dicts:
        {
            'person_id': int,
            'bbox': [x1, y1, x2, y2],
            'confidence': float,
            'keypoints': np.ndarray of shape (17, 3) [x, y, conf],
            'left_wrist': [x, y],
            'right_wrist': [x, y]
        }
        """
        if model_backend is None or not model_backend.is_loaded:
            return []

        try:
            results = model_backend.predict(frame_bgr)
            if not results:
                return []

            res = results[0]
            if not hasattr(res, "keypoints") or res.keypoints is None:
                return []

            poses = []
            boxes = res.boxes.xyxy.cpu().numpy() if res.boxes is not None else []
            confs = res.boxes.conf.cpu().numpy() if res.boxes is not None else []
            kpts_data = res.keypoints.data.cpu().numpy()  # (N, 17, 3)

            for i, kpts in enumerate(kpts_data):
                conf = float(confs[i]) if i < len(confs) else 0.8
                if conf < self.min_confidence:
                    continue

                bbox = boxes[i].tolist() if i < len(boxes) else [0, 0, 0, 0]
                lw = kpts[9][:2].tolist() if kpts[9][2] > 0.2 else None
                rw = kpts[10][:2].tolist() if kpts[10][2] > 0.2 else None

                poses.append({
                    "person_id": i + 1,
                    "bbox": bbox,
                    "confidence": conf,
                    "keypoints": kpts,
                    "left_wrist": lw,
                    "right_wrist": rw,
                })
            return poses
        except Exception:
            return []
