"""Unit tests for domain exception hierarchy."""

import pytest

from orion.core.exceptions import (
    CameraError,
    ConfigurationError,
    HardwareError,
    OrionBaseException,
    SecurityError,
)


@pytest.mark.unit
def test_exception_serialization() -> None:
    """Verify to_dict serialization carries error code and details."""
    exc = CameraError(
        message="Frame drop exceeded safety threshold",
        details={"camera_id": "CAM-01", "dropped_frames": 15},
    )
    data = exc.to_dict()

    assert data["error"] == "CameraError"
    assert data["code"] == "CAMERA_ERROR"
    assert data["message"] == "Frame drop exceeded safety threshold"
    assert data["details"]["camera_id"] == "CAM-01"


@pytest.mark.unit
def test_exception_hierarchy() -> None:
    """Verify all domain errors inherit from OrionBaseException."""
    assert issubclass(ConfigurationError, OrionBaseException)
    assert issubclass(HardwareError, OrionBaseException)
    assert issubclass(SecurityError, OrionBaseException)
