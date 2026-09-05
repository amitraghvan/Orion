"""Core modules for ORION BAS AI Copilot."""

from orion.core.config import OrionSettings, get_settings
from orion.core.exceptions import (
    AudioError,
    CameraError,
    ConfigurationError,
    DatasetError,
    ExperimentError,
    HardwareError,
    HealthError,
    InferenceError,
    ModelLoadError,
    OrionBaseException,
    RecordingError,
    SecurityError,
    StreamingError,
    ValidationError,
)
from orion.core.logger import configure_logging, get_logger

__all__ = [
    "AudioError",
    "CameraError",
    "ConfigurationError",
    "DatasetError",
    "ExperimentError",
    "HardwareError",
    "HealthError",
    "InferenceError",
    "ModelLoadError",
    "OrionBaseException",
    "OrionSettings",
    "RecordingError",
    "SecurityError",
    "StreamingError",
    "ValidationError",
    "configure_logging",
    "get_logger",
    "get_settings",
]
