"""Model metadata and certification schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class QuantizationProfile(BaseModel):
    """Details regarding model precision and calibration."""

    precision: Literal["fp32", "fp16", "int8", "bf16"]
    calibrated_with_dataset: str | None = None
    calibration_samples: int = 0
    quantizer: str | None = None


class ChecksumManifest(BaseModel):
    """Cryptographic integrity specification for flight model artifacts."""

    algorithm: Literal["sha256", "sha512"] = "sha256"
    expected_digest: str
    artifact_size_bytes: int


class ModelMetadata(BaseModel):
    """Complete flight specification for an AI model."""

    model_id: str
    task: Literal["detection", "pose", "activity", "interaction", "segmentation"]
    version: str
    architecture: str
    framework: Literal["onnx", "tensorrt", "openvino", "torchscript"]
    checksum: ChecksumManifest
    quantization: QuantizationProfile
    author: str = "ISRO-BAS AI Team"
    flight_certified: bool = False
    metrics: dict[str, float] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    custom_properties: dict[str, Any] = Field(default_factory=dict)
