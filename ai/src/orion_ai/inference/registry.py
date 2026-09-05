"""Inference engine registry."""

from orion_ai.inference.interfaces import InferenceEngineInterface


class InferenceEngineRegistry:
    """Registry mapping backend names to concrete inference engine classes."""

    _backends: dict[str, type[InferenceEngineInterface]] = {}

    @classmethod
    def register(cls, backend_name: str, backend_cls: type[InferenceEngineInterface]) -> None:
        cls._backends[backend_name] = backend_cls

    @classmethod
    def get(cls, backend_name: str) -> type[InferenceEngineInterface]:
        if backend_name not in cls._backends:
            raise NotImplementedError(
                f"NOT IMPLEMENTED: Inference backend {backend_name} is not registered."
            )
        return cls._backends[backend_name]
