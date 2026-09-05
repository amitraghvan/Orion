"""Centralized domain exception hierarchy for ORION BAS AI Copilot.

All exceptions inherit from OrionBaseException and carry structured error metadata.
Strictly designed for high-reliability aerospace operation.
"""

from typing import Any


class OrionBaseException(Exception):
    """Root exception for all ORION BAS AI Copilot domain errors."""

    def __init__(
        self,
        message: str,
        code: str = "ORION_INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception metadata to structured dictionary."""
        return {
            "error": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"


class ConfigurationError(OrionBaseException):
    """Raised when system configuration loading, validation, or layering fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="CONFIG_ERROR", details=details)


class CameraError(OrionBaseException):
    """Raised when camera capture, stream connection, or frame buffer overflows."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="CAMERA_ERROR", details=details)


class HardwareError(OrionBaseException):
    """Raised when hardware sensor, GPU accelerator, or storage communication fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="HARDWARE_ERROR", details=details)


class DatasetError(OrionBaseException):
    """Raised when dataset loading, format parsing, or integrity verification fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="DATASET_ERROR", details=details)


class ModelLoadError(OrionBaseException):
    """Raised when an AI model weights file fails checksum or runtime loading."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="MODEL_LOAD_ERROR", details=details)


class InferenceError(OrionBaseException):
    """Raised when model forward pass or tensor conversion fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="INFERENCE_ERROR", details=details)


class RecordingError(OrionBaseException):
    """Raised when video pipeline recording, rotation, or storage fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="RECORDING_ERROR", details=details)


class StreamingError(OrionBaseException):
    """Raised when telemetry or video streaming (RTSP/WebRTC/WebSocket) fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="STREAMING_ERROR", details=details)


class ExperimentError(OrionBaseException):
    """Raised when experiment schema validation, step transition, or timeout fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="EXPERIMENT_ERROR", details=details)


class ValidationError(OrionBaseException):
    """Raised when data input or schema verification violates constraints."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="VALIDATION_ERROR", details=details)


class HealthError(OrionBaseException):
    """Raised when subsystem health check detects critical degradation or failure."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="HEALTH_ERROR", details=details)


class SecurityError(OrionBaseException):
    """Raised when path traversal, checksum violation, or security boundary fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="SECURITY_ERROR", details=details)


class AudioError(OrionBaseException):
    """Raised when audio playback, priority alert queue, or speech synthesis fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="AUDIO_ERROR", details=details)
