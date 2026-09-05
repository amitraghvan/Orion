"""Detection model registry."""

from orion_ai.detection.interfaces import DetectorInterface


class DetectorRegistry:
    """Registry mapping detector architectures to implementations."""

    _models: dict[str, type[DetectorInterface]] = {}

    @classmethod
    def register(cls, model_name: str, model_cls: type[DetectorInterface]) -> None:
        cls._models[model_name] = model_cls

    @classmethod
    def get(cls, model_name: str) -> type[DetectorInterface]:
        if model_name not in cls._models:
            raise NotImplementedError(
                f"NOT IMPLEMENTED: Detector model {model_name} is not registered."
            )
        return cls._models[model_name]
