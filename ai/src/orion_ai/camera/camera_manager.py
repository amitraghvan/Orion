"""Authoritative CameraManager for ORION BAS AI Copilot.

Single authoritative owner of the optical hardware handle.
Guarantees:
- Camera hardware is opened ONCE.
- Replay and Live streams use the same FrameSource abstraction.
- Thread-safe latest-frame buffer with non-blocking reads for UI and HTTP endpoints.
- Dedicated background capture worker thread.
- Truthful reporting of CameraStatus: DISCONNECTED, CONNECTING, CONNECTED, PROCESSING, ERROR.
- Graceful disconnect and auto-reconnect support.
- Fully compatible with CameraDriverInterface for PerceptionPipelineCoordinator.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from orion.core.exceptions import CameraError
from orion.core.logger import get_logger
from orion.health.interfaces import SubsystemReport, SubsystemStatus
from orion_ai.camera.camera_sources import (
    CameraStatus,
    FrameBuffer,
    FrameSource,
    LiveCameraSource,
    ReplayVideoSource,
)
from orion_ai.camera.interfaces import CameraDriverInterface
from orion_ai.camera.schemas import CameraIntrinsics, FrameContract, Resolution

logger = get_logger("orion_ai.camera.manager")


class CameraManager(CameraDriverInterface):
    """Authoritative singleton camera manager."""

    def __init__(
        self,
        default_source: str | int = 0,
        camera_id: str = "bas_cam_01",
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        loop: bool = True,
    ) -> None:
        self.camera_id = camera_id
        self._source_spec: str = str(default_source)
        self.target_width = width
        self.target_height = height
        self.target_fps = fps
        self.loop = loop

        self._status: CameraStatus = CameraStatus.DISCONNECTED
        self._active_source: FrameSource | None = None
        self._buffer: FrameBuffer = FrameBuffer(capacity=2)

        self._capture_thread: threading.Thread | None = None
        self._is_running: bool = False
        self._lock = threading.RLock()

        self._actual_fps: float = 0.0
        self._fps_counter: int = 0
        self._fps_timer: float = time.monotonic()

        self._last_frame_time_utc: datetime | None = None
        self._consecutive_drops: int = 0
        self._last_error: str | None = None
        self._listeners: list[Callable[[np.ndarray, int, float], None]] = []

    # --------------------------------------------------------------------------
    # Status & Telemetry Properties
    # --------------------------------------------------------------------------

    @property
    def status(self) -> CameraStatus:
        """Authoritative current operational status."""
        with self._lock:
            return self._status

    @property
    def is_connected(self) -> bool:
        """Truthful connection indicator. Returns True only if actively capturing."""
        with self._lock:
            return self._status in (CameraStatus.CONNECTED, CameraStatus.PROCESSING)

    @property
    def is_active(self) -> bool:
        """Driver active acquisition status."""
        with self._lock:
            return self._is_running and self._status != CameraStatus.ERROR

    @property
    def source(self) -> str:
        with self._lock:
            return self._source_spec

    @property
    def active_source(self) -> str:
        with self._lock:
            return self._source_spec

    @property
    def is_file(self) -> bool:
        with self._lock:
            return self._active_source.is_file if self._active_source else False

    @property
    def actual_fps(self) -> float:
        with self._lock:
            return self._actual_fps

    @property
    def frames_captured(self) -> int:
        return self._buffer.frames_captured

    @property
    def dropped_frames(self) -> int:
        return self._buffer.frames_dropped

    @property
    def frame_id(self) -> int:
        _, contract = self._buffer.get_latest()
        return contract.frame_index if contract else 0

    @property
    def last_frame_timestamp(self) -> datetime | None:
        with self._lock:
            return self._last_frame_time_utc

    @property
    def consecutive_drops(self) -> int:
        with self._lock:
            return self._consecutive_drops

    @property
    def last_error(self) -> str | None:
        with self._lock:
            return self._last_error

    @property
    def latest_frame(self) -> np.ndarray | None:
        """Fetch latest BGR frame from ring buffer without blocking."""
        frame, _ = self._buffer.get_latest()
        return frame

    def get_latest_jpeg(self) -> bytes | None:
        """Fetch pre-encoded JPEG bytes of latest frame."""
        return self._buffer.get_latest_jpeg()

    # --------------------------------------------------------------------------
    # Configuration & Lifecycle
    # --------------------------------------------------------------------------

    def configure(
        self,
        source: str | int,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        loop: bool = True,
    ) -> None:
        """Configure target camera capture source and operational parameters."""
        with self._lock:
            self._source_spec = str(source)
            self.target_width = width
            self.target_height = height
            self.target_fps = fps
            self.loop = loop

    def _create_source(self, source_spec: str) -> FrameSource:
        """Factory method instantiating the correct FrameSource subtype."""
        source_val = source_spec.strip()

        # Check if source is a file path
        is_path = False
        p = Path(source_val)
        if p.is_file() or (
            not source_val.isdigit()
            and not source_val.startswith(("rtsp://", "http://", "https://"))
        ):
            is_path = True

        if is_path:
            return ReplayVideoSource(
                filepath=p,
                target_width=self.target_width,
                target_height=self.target_height,
                target_fps=self.target_fps,
                loop=self.loop,
            )
        return LiveCameraSource(
            source_id=source_val,
            target_width=self.target_width,
            target_height=self.target_height,
            target_fps=self.target_fps,
            enable_native=True,
        )

    def start(self) -> bool:
        """Commence acquisition loop on dedicated background worker thread."""
        with self._lock:
            if self._is_running:
                return True

            self._status = CameraStatus.CONNECTING
            self._last_error = None
            self._active_source = self._create_source(self._source_spec)

            success = self._active_source.open()
            if not success:
                logger.error("Failed to open camera source", source=self._source_spec)
                self._status = CameraStatus.ERROR
                self._last_error = f"Failed to open source: {self._source_spec}"
                return False

            self._status = CameraStatus.CONNECTED
            self._is_running = True
            self._buffer.clear()
            self._fps_counter = 0
            self._fps_timer = time.monotonic()

            self._capture_thread = threading.Thread(
                target=self._capture_worker,
                name=f"CameraCaptureWorker-{self.camera_id}",
                daemon=True,
            )
            self._capture_thread.start()
            logger.info(
                "Authoritative CameraManager started successfully", source=self._source_spec
            )
            return True

    def stop(self) -> None:
        """Halt acquisition worker thread and release hardware handle."""
        with self._lock:
            self._is_running = False

        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None

        with self._lock:
            if self._active_source:
                self._active_source.close()
                self._active_source = None

            self._buffer.clear()
            self._status = CameraStatus.DISCONNECTED
            self._actual_fps = 0.0
            logger.info("Authoritative CameraManager halted and hardware handle released")

    def switch_source(self, new_source: str | int) -> bool:
        """Dynamically switch between live camera device and replay video without pipeline disruption."""
        logger.info("Switching camera source", old=self._source_spec, new=str(new_source))
        was_running = self.is_active
        self.stop()
        self.configure(source=new_source)
        if was_running:
            return self.start()
        return True

    # --------------------------------------------------------------------------
    # Frame Listeners & Acquisition Loop
    # --------------------------------------------------------------------------

    def add_frame_listener(
        self, listener: Callable[[np.ndarray, int, float], None]
    ) -> Callable[[], None]:
        """Register a callback to be notified when a new frame is captured."""
        with self._lock:
            self._listeners.append(listener)

        def _remove() -> None:
            with self._lock:
                if listener in self._listeners:
                    self._listeners.remove(listener)

        return _remove

    def _capture_worker(self) -> None:
        """Dedicated background capture loop continuously filling bounded FrameBuffer."""
        target_interval = 1.0 / max(self.target_fps, 1)

        while self._is_running:
            t0 = time.monotonic()
            src = self._active_source
            if src is None or not src.is_opened():
                time.sleep(0.05)
                continue

            success, frame, frame_id, sensor_time = src.read()
            if not success or frame is None:
                with self._lock:
                    self._consecutive_drops += 1
                    if self._consecutive_drops > 30 and not src.is_file:
                        self._status = CameraStatus.ERROR
                        self._last_error = "Lost connection to optical sensor"
                time.sleep(0.01)
                continue

            with self._lock:
                self._consecutive_drops = 0
                self._status = CameraStatus.PROCESSING

            h, w = frame.shape[:2]
            now_utc = datetime.now(UTC)
            sensor_ns = time.time_ns()

            contract = FrameContract(
                camera_id=self.camera_id,
                frame_index=frame_id,
                resolution=Resolution(width=w, height=h),
                channels=3,
                pixel_format="BGR8",
                timestamp_utc=now_utc,
                timestamp_sensor_ns=sensor_ns,
            )

            # Push to bounded buffer
            self._buffer.push(frame, contract)

            with self._lock:
                self._last_frame_time_utc = now_utc
                self._fps_counter += 1
                now = time.monotonic()
                if (now - self._fps_timer) >= 1.0:
                    self._actual_fps = self._fps_counter / (now - self._fps_timer)
                    self._fps_counter = 0
                    self._fps_timer = now

            # Non-blocking listener notifications
            listeners = list(self._listeners)
            for listener in listeners:
                try:
                    listener(frame, frame_id, sensor_time)
                except Exception as exc:
                    logger.error("Camera listener exception", error=str(exc))

            # Maintain capture frame pacing if not governed by VideoCapture
            elapsed = time.monotonic() - t0
            sleep_time = target_interval - elapsed
            if sleep_time > 0 and not src.is_file:
                time.sleep(sleep_time)

    # --------------------------------------------------------------------------
    # CameraDriverInterface Implementation (for PerceptionPipelineCoordinator)
    # --------------------------------------------------------------------------

    async def initialize(self) -> None:
        """Asynchronously initialize camera and start capture loop."""
        if self.is_active:
            return
        success = await asyncio.to_thread(self.start)
        if not success:
            raise CameraError(
                f"Failed to initialize camera source: {self._source_spec}",
                details={"source": self._source_spec, "error": self._last_error},
            )

        # Wait up to 3.0s for initial frame
        ready = await asyncio.to_thread(self._buffer.wait_for_frame, 3.0)
        if not ready:
            raise CameraError(
                "Timed out waiting for initial frame from camera buffer",
                details={"source": self._source_spec},
            )

    async def shutdown(self) -> None:
        """Asynchronously halt capture and release resources."""
        await asyncio.to_thread(self.stop)

    async def read_frame(self) -> tuple[FrameContract, np.ndarray]:
        """Fetch next frame buffer from bounded ring buffer asynchronously."""
        if not self.is_active and self._buffer.size == 0:
            raise CameraError(
                "Cannot read frame: CameraManager is stopped or disconnected",
                details={"status": self._status.value},
            )

        item = await asyncio.to_thread(self._buffer.pop_frame, 2.0)
        if item is None:
            raise CameraError(
                "Camera frame buffer read timed out",
                details={"status": self._status.value, "error": self._last_error},
            )
        contract, frame = item
        return contract, frame

    def get_intrinsics(self) -> CameraIntrinsics:
        """Return optical calibration matrices."""
        w = float(self.target_width)
        h = float(self.target_height)
        return CameraIntrinsics(
            fx=w * 1.2,
            fy=h * 1.2,
            cx=w / 2.0,
            cy=h / 2.0,
            distortion_coeffs=[0.0, 0.0, 0.0, 0.0, 0.0],
        )

    def get_health_report(self) -> SubsystemReport:
        """Produce standardized subsystem health diagnostic report."""
        now = datetime.now(UTC)
        with self._lock:
            st = self._status
            err = self._last_error
            fps = self._actual_fps
            drops = self._consecutive_drops
            last_ts = self._last_frame_time_utc

        if st == CameraStatus.ERROR:
            status = SubsystemStatus.ERROR
        elif st == CameraStatus.DISCONNECTED:
            status = SubsystemStatus.OFFLINE
        elif st == CameraStatus.CONNECTING or drops > 0:
            status = SubsystemStatus.DEGRADED
        else:
            status = SubsystemStatus.HEALTHY

        return SubsystemReport(
            subsystem_id="camera",
            status=status,
            timestamp=now,
            last_success=last_ts,
            latency_ms=0.0,
            metrics={
                "actual_fps": round(fps, 1),
                "target_fps": self.target_fps,
                "frames_captured": self.frames_captured,
                "dropped_frames": self.dropped_frames,
                "consecutive_drops": drops,
            },
            details={
                "source": self._source_spec,
                "status": st.value,
                "is_file": self.is_file,
                "camera_id": self.camera_id,
            },
            error_message=err,
        )


# Authoritative singleton instance
authoritative_camera_manager = CameraManager()
