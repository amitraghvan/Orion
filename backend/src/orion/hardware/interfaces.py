"""Hardware Abstraction Layer (HAL) interfaces for Bharatiya Antariksh Station.

Architecture only: defines abstract protocols for space-qualified hardware nodes.
Zero hardware implementation. All concrete calls raise NotImplementedError.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class HardwareMetrics(BaseModel):
    """Generic hardware telemetry metric payload."""

    component_id: str
    status: str
    temperature_celsius: float
    power_draw_watts: float
    extra: dict[str, Any] = {}


class CameraInterface(ABC):
    """Abstract interface for high-speed scientific and glovebox cameras."""

    @abstractmethod
    async def open(self, source_uri: str, width: int, height: int, fps: int) -> bool:
        """Establish connection with camera sensor."""
        raise NotImplementedError("NOT IMPLEMENTED: CameraInterface.open")

    @abstractmethod
    async def capture_frame(self) -> Any:
        """Capture a raw frame buffer from the optical sensor."""
        raise NotImplementedError("NOT IMPLEMENTED: CameraInterface.capture_frame")

    @abstractmethod
    async def close(self) -> None:
        """Safely release camera sensor and streaming handles."""
        raise NotImplementedError("NOT IMPLEMENTED: CameraInterface.close")

    @abstractmethod
    async def get_intrinsics(self) -> dict[str, Any]:
        """Retrieve optical calibration parameters (focal length, distortion)."""
        raise NotImplementedError("NOT IMPLEMENTED: CameraInterface.get_intrinsics")


class GPUInterface(ABC):
    """Abstract interface for edge AI accelerators (NVIDIA Jetson, PCIe Workstation)."""

    @abstractmethod
    def get_device_name(self, device_index: int = 0) -> str:
        """Return accelerator model name and vendor."""
        raise NotImplementedError("NOT IMPLEMENTED: GPUInterface.get_device_name")

    @abstractmethod
    def get_memory_stats(self, device_index: int = 0) -> dict[str, int]:
        """Return allocated, reserved, and free memory in bytes."""
        raise NotImplementedError("NOT IMPLEMENTED: GPUInterface.get_memory_stats")

    @abstractmethod
    def get_temperature(self, device_index: int = 0) -> float:
        """Return core thermal readout in Celsius."""
        raise NotImplementedError("NOT IMPLEMENTED: GPUInterface.get_temperature")


class AudioInterface(ABC):
    """Abstract interface for station cockpit / experiment audio transducers."""

    @abstractmethod
    async def play_chime(self, chime_name: str, volume: float) -> None:
        """Emit advisory or warning chime."""
        raise NotImplementedError("NOT IMPLEMENTED: AudioInterface.play_chime")

    @abstractmethod
    async def synthesize_speech(self, text: str, volume: float) -> None:
        """Synthesize offline voice notification."""
        raise NotImplementedError("NOT IMPLEMENTED: AudioInterface.synthesize_speech")

    @abstractmethod
    async def stop(self) -> None:
        """Halt any active audio emission immediately."""
        raise NotImplementedError("NOT IMPLEMENTED: AudioInterface.stop")


class StorageInterface(ABC):
    """Abstract interface for radiation-tolerant flight storage (NVMe / RAM disk)."""

    @abstractmethod
    def get_free_space_mb(self, path: str) -> int:
        """Return available storage in megabytes."""
        raise NotImplementedError("NOT IMPLEMENTED: StorageInterface.get_free_space_mb")

    @abstractmethod
    def is_writable(self, path: str) -> bool:
        """Check write permissions and physical health of partition."""
        raise NotImplementedError("NOT IMPLEMENTED: StorageInterface.is_writable")


class PowerInterface(ABC):
    """Abstract interface for spacecraft power bus monitoring."""

    @abstractmethod
    def get_bus_voltage(self) -> float:
        """Return 28V/120V spacecraft bus voltage."""
        raise NotImplementedError("NOT IMPLEMENTED: PowerInterface.get_bus_voltage")

    @abstractmethod
    def is_auxiliary_power(self) -> bool:
        """Check if operating on battery/auxiliary power reserve."""
        raise NotImplementedError("NOT IMPLEMENTED: PowerInterface.is_auxiliary_power")


class NetworkInterface(ABC):
    """Abstract interface for station internal LAN and air-gapped bus communication."""

    @abstractmethod
    def check_link(self, interface_name: str) -> bool:
        """Return physical Ethernet link carrier state."""
        raise NotImplementedError("NOT IMPLEMENTED: NetworkInterface.check_link")

    @abstractmethod
    def get_bandwidth_usage(self, interface_name: str) -> dict[str, float]:
        """Return current TX/RX bandwidth in megabits per second."""
        raise NotImplementedError("NOT IMPLEMENTED: NetworkInterface.get_bandwidth_usage")
