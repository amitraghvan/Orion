"""Tracker registry."""

from orion_ai.tracking.interfaces import TrackerInterface


class TrackerRegistry:
    """Registry mapping tracking algorithm keys to tracker classes."""

    _trackers: dict[str, type[TrackerInterface]] = {}

    @classmethod
    def register(cls, name: str, tracker_cls: type[TrackerInterface]) -> None:
        cls._trackers[name] = tracker_cls

    @classmethod
    def get(cls, name: str) -> type[TrackerInterface]:
        if name not in cls._trackers:
            raise NotImplementedError(
                f"NOT IMPLEMENTED: Tracker algorithm {name} is not registered."
            )
        return cls._trackers[name]
