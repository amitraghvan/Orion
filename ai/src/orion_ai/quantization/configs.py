"""Quantization configuration schemas."""

from pydantic import BaseModel, Field


class QuantizerConfig(BaseModel):
    """Configuration contract for model calibration and quantization."""

    quantizer_engine: str = "tensorrt"  # tensorrt, onnxruntime, openvino
    cache_calibration: bool = True
    calibration_cache_path: str = "./models/calibration_cache"
    allow_fallback_fp16: bool = True
    tolerance_accuracy_loss_pct: float = Field(default=2.0, ge=0.0)
