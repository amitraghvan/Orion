"""Domain exception hierarchy for ORION BAS AI Copilot."""

from __future__ import annotations


class OrionBaseException(Exception):
    """Base exception for all domain-specific errors in ORION."""

    def __init__(self, message: str, error_code: str = "ORION_ERROR", details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ConfigurationError(OrionBaseException):
    """Raised when application or subsystem configuration fails validation."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, error_code="CONFIG_VALIDATION_ERROR", details=details)


class HardwareError(OrionBaseException):
    """Raised when hardware access (GPU, Camera, Audio) fails."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, error_code="HARDWARE_ERROR", details=details)


class CameraError(HardwareError):
    """Raised when camera initialization, connection, or frame capture fails."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, details=details)
        self.error_code = "CAMERA_ERROR"


class ModelError(OrionBaseException):
    """Raised when model loading, initialization, or inference fails."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, error_code="MODEL_ERROR", details=details)


class ModelNotFoundError(ModelError):
    """Raised when requested model weights file cannot be found."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, details=details)
        self.error_code = "MODEL_NOT_FOUND"


class ProtocolError(OrionBaseException):
    """Raised when experiment protocol loading or validation fails."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, error_code="PROTOCOL_ERROR", details=details)


class ProtocolStateError(ProtocolError):
    """Raised when an invalid state transition is attempted on the protocol FSM."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, details=details)
        self.error_code = "INVALID_STATE_TRANSITION"


class DatabaseError(OrionBaseException):
    """Raised when local database operation fails."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, error_code="DATABASE_ERROR", details=details)


class AudioError(OrionBaseException):
    """Raised when audio annunciation or TTS output fails."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, error_code="AUDIO_ERROR", details=details)


class RecordingError(OrionBaseException):
    """Raised when video recording or file finalization fails."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, error_code="RECORDING_ERROR", details=details)


class StreamingError(OrionBaseException):
    """Raised when IP video streaming fails."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, error_code="STREAMING_ERROR", details=details)
