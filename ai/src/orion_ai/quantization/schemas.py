"""Model quantization schemas."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class CalibrationDatasetSpec(BaseModel):
    """Specification of representative flight calibration dataset."""

    dataset_path: Path
    num_samples: int = Field(default=500, ge=10)
    input_shape: list[int]


class QuantizationSpec(BaseModel):
    """Parameters for post-training quantization (PTQ) or QAT."""

    target_precision: Literal["int8", "fp16"]
    algorithm: Literal["minmax", "entropy", "percentile"] = "entropy"
    per_channel: bool = True
    calibration: CalibrationDatasetSpec | None = None


class QuantizationReport(BaseModel):
    """Outcome report for quantized model artifact."""

    model_id: str
    original_size_bytes: int
    quantized_size_bytes: int
    compression_ratio: float
    accuracy_drop_pct: float = 0.0
    output_path: Path
