"""Security Foundation utilities for ORION BAS AI Copilot.

Provides air-gapped security primitives:
- Safe file path resolution preventing directory traversal attacks.
- Cryptographic hash calculation (SHA-256, SHA-512) for models and recordings.
- Model integrity verification against certified flight manifests.
- Secret masking for logs and telemetry exports.
"""

import hashlib
from pathlib import Path

from orion.core.exceptions import SecurityError


def resolve_safe_path(base_dir: Path | str, untrusted_path: Path | str) -> Path:
    """Resolve and enforce that an untrusted path strictly resides within base_dir.

    Prevents directory traversal attacks (e.g. `../../etc/shadow`).
    """
    base = Path(base_dir).resolve()
    target = (base / untrusted_path).resolve()

    try:
        target.relative_to(base)
    except ValueError as exc:
        raise SecurityError(
            f"Path traversal detected: {untrusted_path} attempts to escape boundary {base}",
            details={"base": str(base), "target": str(target)},
        ) from exc

    return target


def calculate_file_hash(
    file_path: Path | str, algorithm: str = "sha256", chunk_size: int = 65536
) -> str:
    """Compute cryptographic hash of a file using streaming chunks."""
    path = Path(file_path)
    if not path.is_file():
        raise SecurityError(
            f"Cannot compute checksum: file not found at {path}",
            details={"path": str(path)},
        )

    hasher = hashlib.new(algorithm)
    try:
        with path.open("rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
    except Exception as exc:
        raise SecurityError(
            f"Failed to read file for hashing: {exc}",
            details={"path": str(path), "error": str(exc)},
        ) from exc

    return hasher.hexdigest()


def verify_file_integrity(
    file_path: Path | str, expected_hash: str, algorithm: str = "sha256"
) -> bool:
    """Verify that file matches the expected cryptographic digest."""
    calculated = calculate_file_hash(file_path=file_path, algorithm=algorithm)
    if calculated.lower() != expected_hash.lower():
        raise SecurityError(
            f"Integrity check failed for {file_path}. Expected {expected_hash}, got {calculated}",
            details={
                "file_path": str(file_path),
                "expected": expected_hash,
                "calculated": calculated,
            },
        )
    return True


def mask_secret(secret: str, unmasked_suffix_len: int = 4) -> str:
    """Mask sensitive credentials for telemetry or log outputs."""
    if not secret:
        return ""
    if len(secret) <= unmasked_suffix_len:
        return "********"
    masked_part = "*" * (len(secret) - unmasked_suffix_len)
    return f"{masked_part}{secret[-unmasked_suffix_len:]}"
