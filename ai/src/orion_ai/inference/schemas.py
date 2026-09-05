"""Inference engine tensor schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class TensorSpec(BaseModel):
    """Specification of an input/output tensor buffer."""

    name: str
    dtype: Literal["float32", "float16", "int8", "int32", "uint8"]
    shape: list[int]


class InferenceRequest(BaseModel):
    """Execution request containing input tensors."""

    request_id: str
    model_id: str
    input_buffers: dict[str, Any]  # Buffer pointers or numpy arrays


class InferenceOutput(BaseModel):
    """Raw output tensors returned by inference engine."""

    request_id: str
    model_id: str
    output_tensors: dict[str, Any]
    latency_ms: float = Field(ge=0.0)
