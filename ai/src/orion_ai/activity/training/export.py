"""Export utility and manifest generation for ST-GCN Temporal HAR model."""

import argparse
import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import torch

from orion_ai.activity.schemas import TRAINED_ACTIVITY_CLASSES
from orion_ai.activity.stgcn.model import STGCNHARModel

logger = logging.getLogger(__name__)


def compute_sha256(file_path: Path | str) -> str:
    """Compute SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with Path(file_path).open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def generate_manifest(
    model_path: Path | str,
    manifest_path: Path | str,
    model_id: str = "stgcn_har_v1",
    version: str = "1.0.0",
) -> dict[str, Any]:
    """Verify weight file, count parameters, compute checksum, and write manifest JSON."""
    model_path = Path(model_path)
    manifest_path = Path(manifest_path)

    if not model_path.exists():
        raise FileNotFoundError(f"Model file does not exist: {model_path}")

    # Verify model loading
    state_dict = torch.load(model_path, map_location="cpu", weights_only=True)  # nosec B614
    model = STGCNHARModel(in_channels=4, num_classes=len(TRAINED_ACTIVITY_CLASSES))
    model.load_state_dict(state_dict)
    model.eval()

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

    sha256_hash = compute_sha256(model_path)

    manifest_data: dict[str, Any] = {
        "model_id": model_id,
        "version": version,
        "task": "temporal_action_recognition",
        "architecture": "stgcn_coco17",
        "framework": "pytorch",
        "format": "pt",
        "input_shape": [1, 4, 32, 17],
        "output_schema": "class_logits_6",
        "classes": list(TRAINED_ACTIVITY_CLASSES),
        "sha256": sha256_hash,
        "total_parameters": total_params,
        "trainable_parameters": trainable_params,
        "license": "Apache-2.0",
        "source": "orion_ai.activity.training",
        "creation_timestamp": datetime.now(UTC).isoformat(),
        "notes": "ST-GCN model trained on synthetic kinematic microgravity sequences for BAS experiment activity recognition.",
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    logger.info("Manifest successfully created at %s (SHA-256: %s)", manifest_path, sha256_hash)
    return manifest_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate manifest for ST-GCN model.")
    parser.add_argument("--model-path", default="models/weights/stgcn_har_v1.pt")
    parser.add_argument("--manifest-path", default="models/weights/stgcn_har_v1.manifest.json")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    manifest = generate_manifest(args.model_path, args.manifest_path)
    logger.info("Export complete: %s", manifest["model_id"])


if __name__ == "__main__":
    main()
