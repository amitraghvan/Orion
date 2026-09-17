"""Hand perception, spatial association, and contact state machine engine."""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Any

import numpy as np


class ContactState(StrEnum):
    """Temporal contact states between astronaut hand and experiment objects."""

    IDLE = "IDLE"
    APPROACH = "APPROACH"
    TOUCH = "TOUCH"
    MANIPULATE = "MANIPULATE"
    RELEASE = "RELEASE"


class HandObjectInteractionEngine:
    """Detects hands, associates them with experiment objects, and evaluates interaction dynamics."""

    def __init__(self, proximity_threshold_px: float = 120.0) -> None:
        self.proximity_threshold_px = proximity_threshold_px
        self._previous_states: dict[str, ContactState] = {}

    def extract_hands(self, poses: list[dict]) -> list[dict]:
        """Derive hand bounding boxes from wrist and elbow joints."""
        hands = []
        for pose in poses:
            kpts = pose.get("keypoints")
            if kpts is None or len(kpts) < 11:
                continue

            # Left wrist: 9, left elbow: 7
            if kpts[9][2] > 0.3:
                wx, wy = float(kpts[9][0]), float(kpts[9][1])
                ex, ey = (float(kpts[7][0]), float(kpts[7][1])) if kpts[7][2] > 0.3 else (wx, wy - 30)
                box_radius = max(35.0, math.hypot(wx - ex, wy - ey) * 0.4)
                hands.append({
                    "hand_id": f"p{pose['person_id']}_lh",
                    "side": "left",
                    "person_id": pose["person_id"],
                    "center": [wx, wy],
                    "bbox": [wx - box_radius, wy - box_radius, wx + box_radius, wy + box_radius],
                    "confidence": float(kpts[9][2]),
                })

            # Right wrist: 10, right elbow: 8
            if kpts[10][2] > 0.3:
                wx, wy = float(kpts[10][0]), float(kpts[10][1])
                ex, ey = (float(kpts[8][0]), float(kpts[8][1])) if kpts[8][2] > 0.3 else (wx, wy - 30)
                box_radius = max(35.0, math.hypot(wx - ex, wy - ey) * 0.4)
                hands.append({
                    "hand_id": f"p{pose['person_id']}_rh",
                    "side": "right",
                    "person_id": pose["person_id"],
                    "center": [wx, wy],
                    "bbox": [wx - box_radius, wy - box_radius, wx + box_radius, wy + box_radius],
                    "confidence": float(kpts[10][2]),
                })

        return hands

    def evaluate_interactions(self, hands: list[dict], objects: list[dict]) -> list[dict]:
        """Compute interactions between hands and objects based on geometric proximity and IoU."""
        interactions = []

        for hand in hands:
            hx, hy = hand["center"]
            h_box = hand["bbox"]

            for obj in objects:
                # Exclude person bounding boxes
                if obj.get("class_name", "").lower() == "person":
                    continue

                o_box = obj["bbox"]
                ox = (o_box[0] + o_box[2]) * 0.5
                oy = (o_box[1] + o_box[3]) * 0.5

                dist = math.hypot(hx - ox, hy - oy)
                iou = self._compute_box_iou(h_box, o_box)

                # Determine state
                interaction_key = f"{hand['hand_id']}_{obj.get('track_id', obj.get('class_name'))}"
                prev_state = self._previous_states.get(interaction_key, ContactState.IDLE)

                if iou > 0.15:
                    curr_state = ContactState.MANIPULATE
                    action_type = "MANIPULATE"
                elif dist < self.proximity_threshold_px * 0.6:
                    curr_state = ContactState.TOUCH
                    action_type = "TOUCH"
                elif dist < self.proximity_threshold_px:
                    curr_state = ContactState.APPROACH
                    action_type = "APPROACH"
                else:
                    curr_state = ContactState.IDLE
                    action_type = "IDLE"

                self._previous_states[interaction_key] = curr_state

                if curr_state != ContactState.IDLE:
                    interactions.append({
                        "hand_id": hand["hand_id"],
                        "hand_side": hand["side"],
                        "object_class": obj["class_name"],
                        "object_track_id": obj.get("track_id", 0),
                        "state": curr_state.value,
                        "action_type": action_type,
                        "distance_px": round(dist, 1),
                        "iou": round(iou, 3),
                        "vector": [hx, hy, ox, oy],
                        "confidence": round(min(hand["confidence"], obj.get("confidence", 0.8)), 2),
                    })

        return interactions

    @staticmethod
    def _compute_box_iou(box_a: list[float], box_b: list[float]) -> float:
        x_left = max(box_a[0], box_b[0])
        y_top = max(box_a[1], box_b[1])
        x_right = min(box_a[2], box_b[2])
        y_bottom = min(box_a[3], box_b[3])

        if x_right < x_left or y_bottom < y_top:
            return 0.0

        intersection = (x_right - x_left) * (y_bottom - y_top)
        area_a = max(0.0, (box_a[2] - box_a[0]) * (box_a[3] - box_a[1]))
        area_b = max(0.0, (box_b[2] - box_b[0]) * (box_b[3] - box_b[1]))
        union = area_a + area_b - intersection

        return intersection / union if union > 0 else 0.0
