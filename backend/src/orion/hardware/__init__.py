"""Hardware abstraction layer package for ORION BAS AI Copilot."""

from orion.hardware.interfaces import (
    AudioInterface,
    CameraInterface,
    GPUInterface,
    HardwareMetrics,
    NetworkInterface,
    PowerInterface,
    StorageInterface,
)

__all__ = [
    "AudioInterface",
    "CameraInterface",
    "GPUInterface",
    "HardwareMetrics",
    "NetworkInterface",
    "PowerInterface",
    "StorageInterface",
]
