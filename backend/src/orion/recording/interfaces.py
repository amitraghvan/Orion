"""Recording Architecture for ORION BAS AI Copilot.

Architecture only: defines interfaces for video capture pipeline, rotation, metadata,
storage tiering, and sudden power loss recovery.
Zero FFmpeg implementation.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class RecordingMetadata(BaseModel):
    """Archival metadata associated with a video recording segment."""

    recording_id: str
    experiment_id: str
    run_id: str
    camera_id: str
    file_path: Path
    codec: str
    fps: int
    width: int
    height: int
    start_time_utc: str
    end_time_utc: str | None = None
    frame_count: int = 0
    sha256_checksum: str | None = None


class VideoPipelineInterface(ABC):
    """Interface for frame ingestion, hardware encoding, and muxing."""

    @abstractmethod
    async def start_recording(self, metadata: RecordingMetadata) -> None:
        """Initialize encoder and begin file writing pipeline."""
        raise NotImplementedError("NOT IMPLEMENTED: VideoPipelineInterface.start_recording")

    @abstractmethod
    async def write_frame(self, frame_buffer: Any, timestamp_ns: int) -> None:
        """Push raw frame into encoder buffer."""
        raise NotImplementedError("NOT IMPLEMENTED: VideoPipelineInterface.write_frame")

    @abstractmethod
    async def stop_recording(self) -> RecordingMetadata:
        """Flush encoder buffers, finalize video container, and return manifest."""
        raise NotImplementedError("NOT IMPLEMENTED: VideoPipelineInterface.stop_recording")


class StoragePipelineInterface(ABC):
    """Interface for tiering recorded video between high-speed NVMe and cold telemetry storage."""

    @abstractmethod
    async def persist_segment(self, file_path: Path) -> Path:
        """Move recorded segment to permanent station storage."""
        raise NotImplementedError("NOT IMPLEMENTED: StoragePipelineInterface.persist_segment")

    @abstractmethod
    async def enforce_quota(self, max_storage_bytes: int) -> None:
        """Prune oldest non-critical recordings when storage thresholds are breached."""
        raise NotImplementedError("NOT IMPLEMENTED: StoragePipelineInterface.enforce_quota")


class RotationPipelineInterface(ABC):
    """Interface managing scheduled time and file size segment rotation."""

    @abstractmethod
    def should_rotate(self, current_duration_seconds: float, current_size_bytes: int) -> bool:
        """Evaluate whether segment boundary has been reached."""
        raise NotImplementedError("NOT IMPLEMENTED: RotationPipelineInterface.should_rotate")

    @abstractmethod
    async def trigger_rotation(self) -> None:
        """Atomically transition active writer to a new segment without dropping frames."""
        raise NotImplementedError("NOT IMPLEMENTED: RotationPipelineInterface.trigger_rotation")


class MetadataPipelineInterface(ABC):
    """Interface for generating sidecar JSON telemetry manifests and computing checksums."""

    @abstractmethod
    async def generate_sidecar(self, metadata: RecordingMetadata) -> Path:
        """Write JSON sidecar alongside video container."""
        raise NotImplementedError("NOT IMPLEMENTED: MetadataPipelineInterface.generate_sidecar")

    @abstractmethod
    async def compute_manifest_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 digest of video file."""
        raise NotImplementedError(
            "NOT IMPLEMENTED: MetadataPipelineInterface.compute_manifest_checksum"
        )


class RecoveryPipelineInterface(ABC):
    """Interface for repairing corrupted or unfinalized video containers after power failure."""

    @abstractmethod
    async def scan_orphaned_segments(self, directory: Path) -> list[Path]:
        """Discover unfinalized or dangling video segments."""
        raise NotImplementedError(
            "NOT IMPLEMENTED: RecoveryPipelineInterface.scan_orphaned_segments"
        )

    @abstractmethod
    async def repair_segment(self, corrupted_path: Path) -> Path:
        """Recover container moov atom and index indexes."""
        raise NotImplementedError("NOT IMPLEMENTED: RecoveryPipelineInterface.repair_segment")
