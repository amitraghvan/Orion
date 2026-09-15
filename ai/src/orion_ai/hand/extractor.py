"""Pose-based hand region extractor for ORION BAS AI Copilot."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from orion.core.logger import get_logger
from orion_ai.detection.schemas import BoundingBox2D
from orion_ai.hand.interfaces import HandPerceptionInterface
from orion_ai.hand.schemas import HandObservation, HandSide, HandState
from orion_ai.pose.schemas import HumanPose, Keypoint2D
from orion_ai.tracking.schemas import TrackedObject

logger = get_logger("orion_ai.hand.extractor")

COCO_LEFT_WRIST_ID: int = 9
COCO_RIGHT_WRIST_ID: int = 10


class PoseBasedHandExtractor(HandPerceptionInterface):
    """Derives hand bounding regions and confidence states directly from upper-limb skeletal keypoints.

    Eliminates the latency overhead of a dedicated secondary hand network while providing
    stable hand spatial seeds for hand-object association.
    """

    def __init__(
        self,
        padding_px: float = 40.0,
        min_observed_thresh: float = 0.5,
        min_partial_thresh: float = 0.2,
        adaptive_scale: bool = True,
    ) -> None:
        self.padding_px = padding_px
        self.min_observed_thresh = min_observed_thresh
        self.min_partial_thresh = min_partial_thresh
        self.adaptive_scale = adaptive_scale

    def _determine_hand_state(self, score: float | None) -> HandState:
        if score is None or score <= 0.0:
            return HandState.MISSING
        if score >= self.min_observed_thresh:
            return HandState.OBSERVED
        if score >= self.min_partial_thresh:
            return HandState.PARTIAL
        return HandState.OCCLUDED

    def extract_hands(
        self,
        frame_buffer: Any,
        poses: list[HumanPose],
        tracks: list[TrackedObject],
        frame_index: int,
        timestamp: datetime | None = None,
        source_id: str = "primary_payload_camera",
    ) -> list[HandObservation]:
        """Extract hand observations for all associated persons in the frame."""
        if timestamp is None:
            timestamp = datetime.now(UTC)

        observations: list[HandObservation] = []

        # Get frame dimensions if frame_buffer is numpy array
        img_w: float = 1920.0
        img_h: float = 1080.0
        if frame_buffer is not None and hasattr(frame_buffer, "shape") and len(frame_buffer.shape) >= 2:
            img_h = float(frame_buffer.shape[0])
            img_w = float(frame_buffer.shape[1])

        for pose in poses:
            person_id = pose.person_id or 1

            # Compute scale factor if adaptive
            pad = self.padding_px
            if self.adaptive_scale and pose.bbox:
                # Approximate hand size as roughly ~10-15% of person height/diagonal
                person_diag = (pose.bbox.width ** 2 + pose.bbox.height ** 2) ** 0.5
                if person_diag > 10.0:
                    pad = max(20.0, min(80.0, person_diag * 0.08))

            # Look for left and right wrists
            lw_kpt: Keypoint2D | None = None
            rw_kpt: Keypoint2D | None = None

            for kpt in pose.keypoints_2d:
                name_lower = kpt.name.lower()
                if kpt.id == COCO_LEFT_WRIST_ID or "left_wrist" in name_lower or name_lower == "l_wrist":
                    lw_kpt = kpt
                elif kpt.id == COCO_RIGHT_WRIST_ID or "right_wrist" in name_lower or name_lower == "r_wrist":
                    rw_kpt = kpt

            # Process Left Hand
            lw_state = self._determine_hand_state(lw_kpt.score if lw_kpt else None)
            lw_bbox: BoundingBox2D | None = None
            lw_conf = float(lw_kpt.score) if lw_kpt else 0.0
            if lw_kpt and lw_state != HandState.MISSING:
                x_min = max(0.0, lw_kpt.x - pad)
                y_min = max(0.0, lw_kpt.y - pad)
                x_max = min(img_w, lw_kpt.x + pad)
                y_max = min(img_h, lw_kpt.y + pad)
                lw_bbox = BoundingBox2D(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max)

            observations.append(
                HandObservation(
                    hand_id=f"hand_p{person_id}_left",
                    side=HandSide.LEFT,
                    person_track_id=person_id,
                    wrist_keypoint=lw_kpt,
                    region_bbox=lw_bbox,
                    confidence=lw_conf,
                    state=lw_state,
                    frame_index=frame_index,
                    timestamp=timestamp,
                    source_id=source_id,
                )
            )

            # Process Right Hand
            rw_state = self._determine_hand_state(rw_kpt.score if rw_kpt else None)
            rw_bbox: BoundingBox2D | None = None
            rw_conf = float(rw_kpt.score) if rw_kpt else 0.0
            if rw_kpt and rw_state != HandState.MISSING:
                x_min = max(0.0, rw_kpt.x - pad)
                y_min = max(0.0, rw_kpt.y - pad)
                x_max = min(img_w, rw_kpt.x + pad)
                y_max = min(img_h, rw_kpt.y + pad)
                rw_bbox = BoundingBox2D(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max)

            observations.append(
                HandObservation(
                    hand_id=f"hand_p{person_id}_right",
                    side=HandSide.RIGHT,
                    person_track_id=person_id,
                    wrist_keypoint=rw_kpt,
                    region_bbox=rw_bbox,
                    confidence=rw_conf,
                    state=rw_state,
                    frame_index=frame_index,
                    timestamp=timestamp,
                    source_id=source_id,
                )
            )

        return observations
