"""Inference engine configuration schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class InferenceConfig(BaseModel):
    """Configuration contract for model execution runtime."""

    backend: Literal["onnxruntime", "tensorrt", "openvino", "coreml", "cpu"] = "onnxruntime"
    device_id: int = Field(default=0, ge=0)
    enable_profiling: bool = False
    num_threads: int = Field(default=4, ge=1)
    precision: Literal["fp32", "fp16", "int8"] = "fp16"
