"""Core infrastructure module for ORION Desktop System."""

from app.core.config import OrionConfig, get_config, set_config
from app.core.event_bus import event_bus
from app.core.exceptions import (
    AudioError,
    CameraError,
    ConfigurationError,
    DatabaseError,
    HardwareError,
    ModelError,
    ModelNotFoundError,
    OrionBaseException,
    ProtocolError,
    ProtocolStateError,
    RecordingError,
    StreamingError,
)
from app.core.lifecycle import lifecycle
from app.core.logging import configure_logging, get_logger
from app.core.paths import paths
from app.core.state_manager import ApplicationState, state_manager

__all__ = [
    "ApplicationState",
    "AudioError",
    "CameraError",
    "ConfigurationError",
    "DatabaseError",
    "HardwareError",
    "ModelError",
    "ModelNotFoundError",
    "OrionBaseException",
    "OrionConfig",
    "ProtocolError",
    "ProtocolStateError",
    "RecordingError",
    "StreamingError",
    "configure_logging",
    "event_bus",
    "get_config",
    "get_logger",
    "lifecycle",
    "paths",
    "set_config",
    "state_manager",
]
