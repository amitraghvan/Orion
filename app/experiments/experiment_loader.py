"""Protocol loader and cryptographic verification for BAS experiments."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from app.core.exceptions import ProtocolError
from app.core.paths import paths
from app.experiments.experiment_schema import ExperimentSpecification


def compute_protocol_hash(data: dict[str, Any] | ExperimentSpecification) -> str:
    """Compute deterministic SHA-256 fingerprint of experiment specification."""
    if isinstance(data, ExperimentSpecification):
        raw_dict = data.model_dump(exclude={"protocol_hash"})
    else:
        raw_dict = {k: v for k, v in data.items() if k != "protocol_hash"}

    canonical_json = json.dumps(raw_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def load_protocol(file_path: str | Path) -> ExperimentSpecification:
    """Load and validate an experiment protocol from YAML file."""
    path = Path(file_path)
    if not path.is_file():
        resolved = paths.resolve_protocol_path(str(file_path))
        if resolved.is_file():
            path = resolved
        else:
            raise ProtocolError(f"Protocol file not found: {file_path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)

        if not isinstance(raw_data, dict):
            raise ProtocolError(f"Invalid YAML structure in {path}")

        # Compute fingerprint
        sha = compute_protocol_hash(raw_data)
        raw_data["protocol_hash"] = sha

        spec = ExperimentSpecification.model_validate(raw_data)
        return spec
    except Exception as exc:
        raise ProtocolError(f"Failed to load protocol from '{path}': {exc}") from exc


def list_available_protocols() -> list[dict[str, Any]]:
    """Enumerate all available experiment protocol definition files."""
    results = []
    protocol_dirs = [
        paths.experiments_dir / "definitions",
        paths.configs_legacy_dir / "protocols",
        paths.config_dir / "protocols",
    ]

    seen_ids = set()

    for pdir in protocol_dirs:
        if not pdir.is_dir():
            continue
        for yfile in sorted(pdir.glob("*.yaml")):
            try:
                spec = load_protocol(yfile)
                exp_id = spec.metadata.experiment_id
                if exp_id not in seen_ids:
                    seen_ids.add(exp_id)
                    results.append(
                        {
                            "experiment_id": exp_id,
                            "title": spec.metadata.title,
                            "file_path": str(yfile),
                            "total_steps": len(spec.steps),
                            "glovebox_id": spec.metadata.glovebox_id,
                            "sha256": spec.protocol_hash[:12] if spec.protocol_hash else "",
                        }
                    )
            except Exception:
                pass

    return results
