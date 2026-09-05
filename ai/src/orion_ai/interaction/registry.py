"""Interaction module registry."""

from orion_ai.interaction.interfaces import InteractionDetectorInterface


class InteractionRegistry:
    """Registry mapping interaction reasoning algorithms to implementation classes."""

    _detectors: dict[str, type[InteractionDetectorInterface]] = {}

    @classmethod
    def register(cls, name: str, detector_cls: type[InteractionDetectorInterface]) -> None:
        cls._detectors[name] = detector_cls

    @classmethod
    def get(cls, name: str) -> type[InteractionDetectorInterface]:
        if name not in cls._detectors:
            raise NotImplementedError(
                f"NOT IMPLEMENTED: Interaction detector {name} is not registered."
            )
        return cls._detectors[name]
