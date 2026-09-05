"""Inference engine interfaces."""

from abc import ABC, abstractmethod

from orion_ai.inference.schemas import InferenceOutput, InferenceRequest, TensorSpec


class InferenceEngineInterface(ABC):
    """Abstract execution provider for ONNX Runtime, TensorRT, OpenVINO, or CoreML."""

    @abstractmethod
    async def load_model(self, model_path: str) -> None:
        """Load compiled model artifact and prepare execution context."""
        raise NotImplementedError("NOT IMPLEMENTED: InferenceEngineInterface.load_model")

    @abstractmethod
    def get_input_specs(self) -> list[TensorSpec]:
        """Return expected input tensor shapes and dtypes."""
        raise NotImplementedError("NOT IMPLEMENTED: InferenceEngineInterface.get_input_specs")

    @abstractmethod
    def get_output_specs(self) -> list[TensorSpec]:
        """Return generated output tensor specifications."""
        raise NotImplementedError("NOT IMPLEMENTED: InferenceEngineInterface.get_output_specs")

    @abstractmethod
    async def forward(self, request: InferenceRequest) -> InferenceOutput:
        """Execute accelerated forward pass."""
        raise NotImplementedError("NOT IMPLEMENTED: InferenceEngineInterface.forward")

    @abstractmethod
    async def unload_model(self) -> None:
        """Release GPU context and buffers."""
        raise NotImplementedError("NOT IMPLEMENTED: InferenceEngineInterface.unload_model")
