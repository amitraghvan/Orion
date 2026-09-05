"""Model quantizer interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from orion_ai.quantization.schemas import QuantizationReport, QuantizationSpec


class ModelQuantizerInterface(ABC):
    """Interface for edge accelerator quantization (TensorRT PTQ / ONNX Runtime INT8)."""

    @abstractmethod
    async def quantize(
        self, input_model_path: Path, spec: QuantizationSpec, output_dir: Path
    ) -> QuantizationReport:
        """Run post-training calibration and export compressed weights."""
        raise NotImplementedError("NOT IMPLEMENTED: ModelQuantizerInterface.quantize")
