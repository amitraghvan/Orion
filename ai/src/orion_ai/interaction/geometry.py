"""Geometric interaction metrics and microgravity-robust spatial feature extractors."""

from __future__ import annotations

import math
from dataclasses import dataclass

from orion_ai.detection.schemas import BoundingBox2D
from orion_ai.geometry.iou import (
    compute_bbox_overlap_ratio,
    compute_center_distance,
    compute_center_offset,
    normalize_distance,
)
from orion_ai.hand.schemas import HandObservation
from orion_ai.interaction.object_schemas import ObjectObservation


@dataclass
class GeometricInteractionFeatures:
    """Calculated relational features between a single hand and target object."""

    center_distance_px: float
    normalized_distance: float
    overlap_ratio: float
    center_offset: tuple[float, float]
    approach_velocity: float = 0.0
    is_near: bool = False
    is_in_contact: bool = False


class InteractionGeometryCalculator:
    """Microgravity-robust geometry engine computing invariant relational features."""

    def __init__(
        self,
        near_threshold_norm: float = 0.35,
        contact_threshold_norm: float = 0.05,
        min_overlap_ratio: float = 0.10,
    ) -> None:
        self.near_threshold_norm = near_threshold_norm
        self.contact_threshold_norm = contact_threshold_norm
        self.min_overlap_ratio = min_overlap_ratio

    def compute_features(
        self,
        hand: HandObservation,
        obj: ObjectObservation,
        reference_diagonal: float = 1000.0,
        prev_normalized_distance: float | None = None,
    ) -> GeometricInteractionFeatures:
        """Compute relational geometric features between a hand and an object."""
        # Determine effective hand bounding box
        hand_box = hand.region_bbox
        if hand_box is None:
            # Fallback to zero-area box around wrist keypoint or origin
            if hand.wrist_keypoint:
                x = hand.wrist_keypoint.x
                y = hand.wrist_keypoint.y
                hand_box = BoundingBox2D(x_min=x - 20, y_min=y - 20, x_max=x + 20, y_max=y + 20)
            else:
                hand_box = BoundingBox2D(x_min=0, y_min=0, x_max=0, y_max=0)

        obj_box = obj.bbox

        dist_px = compute_center_distance(hand_box, obj_box)
        norm_dist = normalize_distance(dist_px, reference_diagonal)
        overlap = compute_bbox_overlap_ratio(hand_box, obj_box)
        offset = compute_center_offset(hand_box, obj_box)

        velocity = 0.0
        if prev_normalized_distance is not None:
            # Positive velocity means approaching (distance decreasing)
            velocity = prev_normalized_distance - norm_dist

        is_contact = (norm_dist <= self.contact_threshold_norm) or (overlap >= self.min_overlap_ratio)
        is_near = is_contact or (norm_dist <= self.near_threshold_norm)

        return GeometricInteractionFeatures(
            center_distance_px=dist_px,
            normalized_distance=norm_dist,
            overlap_ratio=overlap,
            center_offset=offset,
            approach_velocity=velocity,
            is_near=is_near,
            is_in_contact=is_contact,
        )


def compute_motion_correlation(
    hand_vel: tuple[float, float],
    obj_vel: tuple[float, float],
    min_speed: float = 2.0,
) -> float:
    """Compute cosine similarity of motion vectors between hand and object.

    High correlation (>0.7) during contact indicates physical manipulation.
    """
    speed_h = math.sqrt(hand_vel[0] ** 2 + hand_vel[1] ** 2)
    speed_o = math.sqrt(obj_vel[0] ** 2 + obj_vel[1] ** 2)

    if speed_h < min_speed or speed_o < min_speed:
        return 0.0

    dot = hand_vel[0] * obj_vel[0] + hand_vel[1] * obj_vel[1]
    return max(-1.0, min(1.0, dot / (speed_h * speed_o)))
