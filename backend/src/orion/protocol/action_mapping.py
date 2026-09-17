from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


class ActivityToActionMapper:
    """Translates neural network activity classifications into protocol action vocabulary.

    Ensures that unmapped, unknown, or runtime status flags do not generate invalid
    actions, upholding the safety invariant that UNKNOWN != WRONG.
    """

    # Canonical 1:1 mapping for Phase 1.3 ST-GCN classes
    DEFAULT_CANONICAL_MAPPING: dict[str, str] = {
        "prepare_workstation": "prepare_workstation",
        "reach_tool": "reach_tool",
        "grasp_tool": "grasp_tool",
        "manipulate_sample": "manipulate_sample",
        "inspect_chamber": "inspect_chamber",
        "idle": "idle",
        # Common variations / aliases
        "prepare": "prepare_workstation",
        "reach": "reach_tool",
        "grasp": "grasp_tool",
        "manipulate": "manipulate_sample",
        "inspect": "inspect_chamber",
        "standby": "idle",
        # BAS Real Experiments Vocabulary
        "pick_yellow": "pick_yellow",
        "place_yellow": "place_yellow",
        "pick_red": "pick_red",
        "place_red": "place_red",
        "move_box": "move_box",
        "move_red_to_yellow": "move_red_to_yellow",
        "move_yellow_to_red": "move_yellow_to_red",
        "check_box": "check_box",
        "check_yellow": "check_yellow",
        "check_red": "check_red",
        "overlap_boxes": "overlap_boxes",
        "overlap_yellow_on_red": "overlap_yellow_on_red",
        "overlap_red_on_yellow": "overlap_red_on_yellow",
        "pick_both": "pick_both",
        "place_both": "place_both",
        "pick": "pick",
        "place": "place",
        "move": "move",
        "check": "check",
        "overlap": "overlap",
    }

    # Set of runtime status labels that are not physical actions
    NON_ACTION_STATUSES: set[str] = {
        "unknown",
        "uncertain",
        "warming_up",
        "degraded",
        "nominal",
        "none",
    }

    def __init__(self, custom_mapping: Mapping[str, str] | None = None) -> None:
        self._mapping: dict[str, str] = dict(self.DEFAULT_CANONICAL_MAPPING)
        if custom_mapping:
            for k, v in custom_mapping.items():
                self._mapping[k.strip().lower()] = v.strip().lower()

    def map_activity(self, raw_activity: str | None) -> str:
        """Map raw activity classification string to protocol action name.

        Returns 'UNKNOWN' if activity is empty, non-action status, or unrecognized.
        """
        if not raw_activity:
            return "UNKNOWN"

        normalized = raw_activity.strip().lower()

        if normalized in self.NON_ACTION_STATUSES:
            return "UNKNOWN"

        return self._mapping.get(normalized, "UNKNOWN")

    def is_known_action(self, action: str) -> bool:
        """Check if action is in recognized protocol action vocabulary."""
        return (
            action.strip().lower() in self._mapping.values() and action.strip().lower() != "unknown"
        )
