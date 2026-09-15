"""Shared bounding-box geometry functions for detection, tracking, and interaction modules."""

from __future__ import annotations

import math

from orion_ai.detection.schemas import BoundingBox2D


def compute_bbox_iou(b1: BoundingBox2D, b2: BoundingBox2D) -> float:
    """Compute Intersection over Union between two 2D bounding boxes."""
    x_left = max(b1.x_min, b2.x_min)
    y_top = max(b1.y_min, b2.y_min)
    x_right = min(b1.x_max, b2.x_max)
    y_bottom = min(b1.y_max, b2.y_max)

    if x_right <= x_left or y_bottom <= y_top:
        return 0.0

    intersection = (x_right - x_left) * (y_bottom - y_top)
    area1 = b1.width * b1.height
    area2 = b2.width * b2.height
    union = area1 + area2 - intersection

    return float(intersection / union) if union > 0 else 0.0


def compute_bbox_center(box: BoundingBox2D) -> tuple[float, float]:
    """Return (cx, cy) center coordinates of a bounding box."""
    return ((box.x_min + box.x_max) / 2.0, (box.y_min + box.y_max) / 2.0)


def compute_center_distance(b1: BoundingBox2D, b2: BoundingBox2D) -> float:
    """Compute Euclidean distance between bounding box centers."""
    c1 = compute_bbox_center(b1)
    c2 = compute_bbox_center(b2)
    return math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2)


def compute_center_offset(source: BoundingBox2D, target: BoundingBox2D) -> tuple[float, float]:
    """Compute directional vector from source center to target center."""
    s = compute_bbox_center(source)
    t = compute_bbox_center(target)
    return (t[0] - s[0], t[1] - s[1])


def compute_bbox_overlap_ratio(inner: BoundingBox2D, outer: BoundingBox2D) -> float:
    """Compute fraction of 'inner' box area that overlaps with 'outer' box.

    Different from IoU — this is asymmetric. Useful for checking how much
    of a hand region overlaps with an object region.
    """
    x_left = max(inner.x_min, outer.x_min)
    y_top = max(inner.y_min, outer.y_min)
    x_right = min(inner.x_max, outer.x_max)
    y_bottom = min(inner.y_max, outer.y_max)

    if x_right <= x_left or y_bottom <= y_top:
        return 0.0

    intersection = (x_right - x_left) * (y_bottom - y_top)
    inner_area = inner.width * inner.height

    return float(intersection / inner_area) if inner_area > 0 else 0.0


def compute_bbox_diagonal(box: BoundingBox2D) -> float:
    """Compute diagonal length of a bounding box (for normalization)."""
    return math.sqrt(box.width ** 2 + box.height ** 2)


def normalize_distance(distance: float, reference_diagonal: float, epsilon: float = 1e-6) -> float:
    """Normalize a pixel distance relative to a reference diagonal (e.g. person bbox)."""
    return distance / max(reference_diagonal, epsilon)
