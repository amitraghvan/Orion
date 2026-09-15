"""Subsystem Health Monitoring Interfaces for ORION BAS AI Copilot.

Architecture only: defines structured health contracts across 10 vital space station AI subsystems.
Zero monitoring implementation.
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SubsystemStatus(StrEnum):
    """Aerospace subsystem health severity rating."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    OFFLINE = "OFFLINE"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class SubsystemReport(BaseModel):
    """Standardized health check diagnostic report."""

    subsystem_id: str
    status: SubsystemStatus
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    latency_ms: float = 0.0
    last_success: datetime | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None


class BaseHealthChecker(ABC):
    """Abstract contract for individual subsystem health interrogators."""

    @property
    @abstractmethod
    def subsystem_id(self) -> str:
        """Unique identifier of the subsystem."""
        raise NotImplementedError("NOT IMPLEMENTED: BaseHealthChecker.subsystem_id")

    @abstractmethod
    async def check_health(self) -> SubsystemReport:
        """Execute non-blocking diagnostic and return health report."""
        raise NotImplementedError(f"NOT IMPLEMENTED: Health probe for {self.subsystem_id}")


class CameraHealthChecker(BaseHealthChecker):
    """Interrogates optical sensors, FPS stability, and frame drops."""

    @property
    def subsystem_id(self) -> str:
        return "camera"

    async def check_health(self) -> SubsystemReport:
        raise NotImplementedError("NOT IMPLEMENTED: CameraHealthChecker.check_health")


class GPUHealthChecker(BaseHealthChecker):
    """Monitors GPU core temperature, VRAM allocation, and ECC memory errors."""

    @property
    def subsystem_id(self) -> str:
        return "gpu"

    async def check_health(self) -> SubsystemReport:
        raise NotImplementedError("NOT IMPLEMENTED: GPUHealthChecker.check_health")


class CPUHealthChecker(BaseHealthChecker):
    """Monitors CPU load across all cores, thermal throttling, and context switches."""

    @property
    def subsystem_id(self) -> str:
        return "cpu"

    async def check_health(self) -> SubsystemReport:
        raise NotImplementedError("NOT IMPLEMENTED: CPUHealthChecker.check_health")


class MemoryHealthChecker(BaseHealthChecker):
    """Monitors system RAM utilization, swap usage, and page faults."""

    @property
    def subsystem_id(self) -> str:
        return "memory"

    async def check_health(self) -> SubsystemReport:
        raise NotImplementedError("NOT IMPLEMENTED: MemoryHealthChecker.check_health")


class DiskHealthChecker(BaseHealthChecker):
    """Monitors available partition capacity, write latency, and filesystem integrity."""

    @property
    def subsystem_id(self) -> str:
        return "disk"

    async def check_health(self) -> SubsystemReport:
        raise NotImplementedError("NOT IMPLEMENTED: DiskHealthChecker.check_health")


class AudioHealthChecker(BaseHealthChecker):
    """Verifies audio transducer connectivity and alert queue responsiveness."""

    @property
    def subsystem_id(self) -> str:
        return "audio"

    async def check_health(self) -> SubsystemReport:
        raise NotImplementedError("NOT IMPLEMENTED: AudioHealthChecker.check_health")


class RecorderHealthChecker(BaseHealthChecker):
    """Monitors video encoding pipelines, frame drop rate, and segment rotation."""

    @property
    def subsystem_id(self) -> str:
        return "recorder"

    async def check_health(self) -> SubsystemReport:
        raise NotImplementedError("NOT IMPLEMENTED: RecorderHealthChecker.check_health")


class StreamerHealthChecker(BaseHealthChecker):
    """Monitors RTSP/WebRTC streamer socket state and outgoing client bandwidth."""

    @property
    def subsystem_id(self) -> str:
        return "streamer"

    async def check_health(self) -> SubsystemReport:
        raise NotImplementedError("NOT IMPLEMENTED: StreamerHealthChecker.check_health")


class ModelRuntimeHealthChecker(BaseHealthChecker):
    """Verifies TensorRT / ONNX runtime engine execution latency and watchdog."""

    @property
    def subsystem_id(self) -> str:
        return "model_runtime"

    async def check_health(self) -> SubsystemReport:
        raise NotImplementedError("NOT IMPLEMENTED: ModelRuntimeHealthChecker.check_health")


class ApiHealthChecker(BaseHealthChecker):
    """Interrogates internal HTTP and WebSocket routing pipelines."""

    @property
    def subsystem_id(self) -> str:
        return "api"

    async def check_health(self) -> SubsystemReport:
        raise NotImplementedError("NOT IMPLEMENTED: ApiHealthChecker.check_health")
