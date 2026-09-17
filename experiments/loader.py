"""Protocol loader, validator, and cryptographic hashing utilities."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from experiments.schemas import ExperimentSpecification


class ProtocolError(Exception):
    """Base exception for protocol loading and validation."""


class ProtocolLoadError(ProtocolError):
    """Raised when protocol file cannot be read or parsed."""


class ProtocolValidationError(ProtocolError):
    """Raised when protocol specification fails semantic/structural validation."""


class ProtocolIntegrityError(ProtocolError):
    """Raised when protocol cryptographic hash verification fails."""


def compute_protocol_hash(data: dict[str, Any] | ExperimentSpecification) -> str:
    """Compute deterministic SHA-256 hash of experiment specification.

    Excludes volatile fields like 'protocol_hash' to produce an invariant fingerprint.
    """
    if isinstance(data, ExperimentSpecification):
        raw_dict = data.model_dump(exclude={"protocol_hash"})
    else:
        raw_dict = {k: v for k, v in data.items() if k != "protocol_hash"}

    # Deterministic JSON serialization
    canonical_json = json.dumps(raw_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def load_protocol(file_path: str | Path) -> ExperimentSpecification:
    """Load and validate an experiment protocol from YAML or JSON file.

    Performs:
    1. File reading and parsing (YAML / JSON).
    2. Pydantic schema validation.
    3. Structural & semantic validation (ordering, unique IDs, valid transition targets).
    4. Deterministic SHA-256 hashing stamped into `spec.protocol_hash`.
    """
    path = Path(file_path).resolve()
    if not path.is_file():
        raise ProtocolLoadError(f"Protocol file not found: {path}")

    try:
        with path.open(encoding="utf-8") as f:
            raw_content = yaml.safe_load(f)
    except Exception as e:
        raise ProtocolLoadError(f"Failed to parse protocol file {path}: {e}") from e

    if not isinstance(raw_content, dict):
        raise ProtocolValidationError(
            f"Invalid protocol root: expected dict, got {type(raw_content).__name__}"
        )

    try:
        spec = ExperimentSpecification.model_validate(raw_content)
    except Exception as e:
        raise ProtocolValidationError(f"Schema validation failed for {path}: {e}") from e

    # Structural validations
    if not spec.steps:
        raise ProtocolValidationError(
            f"Protocol {spec.metadata.experiment_id} must contain at least 1 step"
        )

    step_ids = set()
    step_numbers = set()
    for s in spec.steps:
        if s.step_id in step_ids:
            raise ProtocolValidationError(f"Duplicate step_id '{s.step_id}' in protocol")
        step_ids.add(s.step_id)

        if s.step_number in step_numbers:
            raise ProtocolValidationError(f"Duplicate step_number {s.step_number} in protocol")
        step_numbers.add(s.step_number)

    # Validate transition targets
    for s in spec.steps:
        for target in s.allowed_transitions:
            if target not in step_ids:
                raise ProtocolValidationError(
                    f"Step '{s.step_id}' references unknown allowed_transition target '{target}'"
                )

    # Compute and stamp cryptographic SHA-256 fingerprint
    spec.protocol_hash = compute_protocol_hash(spec)
    return spec


def verify_protocol_integrity(spec: ExperimentSpecification, expected_hash: str) -> bool:
    """Verify that an ExperimentSpecification matches an expected SHA-256 hash."""
    current_hash = compute_protocol_hash(spec)
    return current_hash.lower() == expected_hash.strip().lower()
