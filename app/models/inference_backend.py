"""Abstract inference backend contract supporting PyTorch, ONNX Runtime, and TensorRT."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class InferenceBackend(ABC):
    """Polymorphic model execution engine interface."""

    def __init__(self, model_path: str, device: str = "auto") -> None:
        self.model_path = model_path
        self.device = device
        self._is_loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    @abstractmethod
    def load(self) -> bool:
        """Load model weights and allocate execution memory."""
        raise NotImplementedError

    @abstractmethod
    def predict(self, input_data: Any) -> Any:
        """Run forward inference."""
        raise NotImplementedError

    @abstractmethod
    def unload(self) -> None:
        """Release GPU / RAM resources."""
        raise NotImplementedError
