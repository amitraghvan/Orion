"""Unit tests for LocalModelWeightsLoader verifying cryptographic SHA-256 integrity."""

from pathlib import Path

import pytest

from orion.core.exceptions import SecurityError
from orion_ai.models.loader import LocalModelWeightsLoader
from orion_ai.models.schemas import ChecksumManifest, ModelMetadata, QuantizationProfile


@pytest.mark.asyncio
@pytest.mark.unit
async def test_model_loader_success() -> None:
    """Verify loading real weights with correct SHA-256 hash succeeds."""
    loader = LocalModelWeightsLoader(base_models_dir="models/weights")

    metadata = ModelMetadata(
        model_id="yolo11n",
        task="detection",
        version="11.0.0",
        architecture="yolo11n",
        framework="torchscript",
        checksum=ChecksumManifest(
            algorithm="sha256",
            expected_digest="0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1",
            artifact_size_bytes=5623088,
        ),
        quantization=QuantizationProfile(precision="fp32"),
        custom_properties={"file_path": "yolo11n.pt"},
    )

    path = await loader.fetch_and_verify(metadata)
    assert path.is_file()
    assert path.name == "yolo11n.pt"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_model_loader_hash_mismatch() -> None:
    """Verify corrupted hash causes SecurityError with MODEL_INTEGRITY_FAILURE."""
    loader = LocalModelWeightsLoader(base_models_dir="models/weights")

    metadata = ModelMetadata(
        model_id="yolo11n",
        task="detection",
        version="11.0.0",
        architecture="yolo11n",
        framework="torchscript",
        checksum=ChecksumManifest(
            algorithm="sha256",
            expected_digest="deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
            artifact_size_bytes=5623088,
        ),
        quantization=QuantizationProfile(precision="fp32"),
        custom_properties={"file_path": "yolo11n.pt"},
    )

    with pytest.raises(SecurityError) as exc_info:
        await loader.fetch_and_verify(metadata)

    assert exc_info.value.code == "SECURITY_ERROR"
    assert exc_info.value.details.get("subcode") == "MODEL_INTEGRITY_FAILURE"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_model_loader_missing_file() -> None:
    """Verify loading nonexistent model raises FileNotFoundError."""
    loader = LocalModelWeightsLoader(base_models_dir="models/weights")

    metadata = ModelMetadata(
        model_id="missing_model",
        task="detection",
        version="1.0.0",
        architecture="yolo",
        framework="torchscript",
        checksum=ChecksumManifest(
            algorithm="sha256",
            expected_digest="0000000000000000000000000000000000000000000000000000000000000000",
            artifact_size_bytes=0,
        ),
        quantization=QuantizationProfile(precision="fp32"),
        custom_properties={"file_path": "nonexistent.pt"},
    )

    with pytest.raises(FileNotFoundError):
        await loader.fetch_and_verify(metadata)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_model_loader_manifest_task_mismatch() -> None:
    """Verify loading weights with mismatched task in manifest raises SecurityError."""
    loader = LocalModelWeightsLoader(base_models_dir="models/weights")

    # yolo11n.manifest.json declares task="detection", but metadata claims task="pose"
    metadata = ModelMetadata(
        model_id="yolo11n",
        task="pose",
        version="11.0.0",
        architecture="yolo11n",
        framework="torchscript",
        checksum=ChecksumManifest(
            algorithm="sha256",
            expected_digest="0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1",
            artifact_size_bytes=5623088,
        ),
        quantization=QuantizationProfile(precision="fp32"),
        custom_properties={"file_path": "yolo11n.pt"},
    )

    with pytest.raises(SecurityError) as exc_info:
        await loader.fetch_and_verify(metadata)

    assert exc_info.value.code == "SECURITY_ERROR"
    assert exc_info.value.details.get("subcode") == "MODEL_MANIFEST_MISMATCH"

