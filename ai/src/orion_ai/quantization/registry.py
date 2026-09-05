"""Quantizer engine registry."""

from orion_ai.quantization.interfaces import ModelQuantizerInterface


class QuantizerRegistry:
    """Registry mapping quantization backends to implementations."""

    _quantizers: dict[str, type[ModelQuantizerInterface]] = {}

    @classmethod
    def register(cls, engine_name: str, quantizer_cls: type[ModelQuantizerInterface]) -> None:
        cls._quantizers[engine_name] = quantizer_cls

    @classmethod
    def get(cls, engine_name: str) -> type[ModelQuantizerInterface]:
        if engine_name not in cls._quantizers:
            raise NotImplementedError(
                f"NOT IMPLEMENTED: Quantizer engine {engine_name} is not registered."
            )
        return cls._quantizers[engine_name]
