"""OpenCV camera driver with dedicated background capture thread and bounded ring buffer."""

import asyncio
import threading
import time
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from orion.core.exceptions import CameraError
from orion.core.logger import get_logger
from orion.health.interfaces import SubsystemReport, SubsystemStatus
from orion_ai.camera.interfaces import CameraDriverInterface
from orion_ai.camera.schemas import CameraIntrinsics, FrameContract, Resolution

logger = get_logger("orion_ai.camera.opencv")

MAX_TRANSIENT_DROPS: int = 30
RING_BUFFER_CAPACITY: int = 2


class OpenCVCameraDriver(CameraDriverInterface):
    """Concrete camera driver with dedicated capture thread, bounded ring buffer, and fault isolation."""

    def __init__(
        self,
        source: str | int = 0,
        camera_id: str = "bas_cam_01",
        target_fps: int = 30,
        width: int = 640,
        height: int = 480,
        loop: bool = True,
        is_replay_fallback: bool = False,
    ) -> None:
        self.source = source
        self.camera_id = camera_id
        self.target_fps = target_fps
        self.target_width = width
        self.target_height = height
        self.loop = loop
        self.is_replay_fallback = is_replay_fallback

        self._cap: cv2.VideoCapture | None = None
        self._frame_index: int = 0
        self._dropped_frames: int = 0
        self._consecutive_drops: int = 0
        self._last_frame_time_utc: datetime | None = None
        self._is_active: bool = False
        self._is_file: bool = False
        self._eos_reached: bool = False
        self._fatal_error: CameraError | None = None

        # Bounded ring buffer isolating capture timing from pipeline processing
        self._ring_buffer: deque[tuple[FrameContract, np.ndarray[Any, Any]]] = deque(
            maxlen=RING_BUFFER_CAPACITY
        )
        self._buffer = self._ring_buffer
        self._buffer_lock = threading.Lock()
        self._frame_ready_event = threading.Event()
        self._frame_consumed_event = threading.Event()
        self._frame_consumed_event.set()
        self._capture_thread: threading.Thread | None = None
        self._worker: threading.Thread | None = None

    @property
    def is_active(self) -> bool:
        """Return driver active acquisition status."""
        return self._is_active

    @property
    def dropped_frames(self) -> int:
        """Return total dropped or skipped frames."""
        return self._dropped_frames

    @property
    def frames_captured(self) -> int:
        """Return total frames captured from device."""
        return self._frame_index

    @property
    def last_frame_timestamp(self) -> datetime | None:
        """Return timestamp of the most recent frame."""
        return self._last_frame_time_utc

    @property
    def consecutive_drops(self) -> int:
        """Return current consecutive frame drop count."""
        return self._consecutive_drops

    @property
    def last_error(self) -> str | None:
        """Return last fatal error message if any."""
        return str(self._fatal_error) if self._fatal_error else None

    @property
    def active_source(self) -> str | int:
        """Return active capture device or file source."""
        return self.source

    def get_health_report(self) -> SubsystemReport:
        """Return standardized subsystem health diagnostic report."""
        now = datetime.now(UTC)
        if self._fatal_error:
            status = SubsystemStatus.ERROR
            err_msg = str(self._fatal_error)
        elif not self._is_active:
            status = SubsystemStatus.OFFLINE
            err_msg = "Camera driver not initialized or stopped"
        elif self.is_replay_fallback:
            status = SubsystemStatus.DEGRADED
            err_msg = "Replay video fallback active"
        elif self._consecutive_drops > 0:
            status = SubsystemStatus.DEGRADED
            err_msg = f"Experiencing transient frame drops ({self._consecutive_drops})"
        else:
            status = SubsystemStatus.HEALTHY
            err_msg = None

        return SubsystemReport(
            subsystem_id="camera",
            status=status,
            timestamp=now,
            last_success=self._last_frame_time_utc,
            latency_ms=0.0,
            metrics={
                "frames_captured": self._frame_index,
                "dropped_frames": self._dropped_frames,
                "consecutive_drops": self._consecutive_drops,
                "target_fps": self.target_fps,
            },
            details={
                "source": str(self.source),
                "is_file": self._is_file,
                "is_replay_fallback": self.is_replay_fallback,
                "camera_id": self.camera_id,
            },
            error_message=err_msg,
        )

    async def initialize(self) -> None:
        """Initialize optical sensor and launch dedicated capture thread."""
        if self._is_active:
            return

        # Determine if source is video file or camera index
        if isinstance(self.source, str) and not self.source.isdigit():
            path = Path(self.source)
            if not path.exists():
                raise CameraError(
                    f"Video source file not found: {self.source}",
                    details={"source": str(self.source), "subcode": "CAMERA_FILE_NOT_FOUND"},
                )
            self._is_file = True
            self._cap = cv2.VideoCapture(str(path))
        else:
            dev_idx = int(self.source)
            self._cap = cv2.VideoCapture(dev_idx)

        if not self._cap or not self._cap.isOpened():
            raise CameraError(
                f"Failed to open video source: {self.source}",
                details={"source": str(self.source), "subcode": "CAMERA_DEVICE_UNAVAILABLE"},
            )

        # Configure camera capture properties if not a static video file
        if not self._is_file:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
            self._cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        self._is_active = True
        self._eos_reached = False
        self._fatal_error = None
        self._frame_index = 0
        self._frame_ready_event.clear()
        with self._buffer_lock:
            self._ring_buffer.clear()

        # Launch dedicated capture worker thread
        self._capture_thread = threading.Thread(
            target=self._capture_worker,
            name=f"CaptureWorker-{self.camera_id}",
            daemon=True,
        )
        self._worker = self._capture_thread
        self._capture_thread.start()

        # Wait up to 3.0s for first frame to ensure capture thread is live
        try:
            await asyncio.to_thread(self._wait_for_first_frame, 3.0)
        except Exception as exc:
            await self.shutdown()
            raise CameraError(
                f"Capture worker failed to produce initial frame: {exc}",
                details={"subcode": "CAMERA_INIT_TIMEOUT"},
            ) from exc

        logger.info(
            "Camera driver initialized with dedicated capture thread",
            camera_id=self.camera_id,
            source=str(self.source),
            is_file=self._is_file,
            target_fps=self.target_fps,
            ring_buffer_capacity=RING_BUFFER_CAPACITY,
        )

    def _wait_for_first_frame(self, timeout_s: float) -> None:
        """Block worker thread briefly until initial frame arrives in buffer."""
        ready = self._frame_ready_event.wait(timeout=timeout_s)
        if not ready and self._fatal_error:
            raise self._fatal_error
        if not ready:
            raise TimeoutError("Capture thread timed out waiting for initial frame")

    def _capture_worker(self) -> None:
        """Dedicated background capture loop continuously filling bounded ring buffer."""
        consecutive_drops = 0
        last_frame_time = time.perf_counter()

        while self._is_active and self._cap:
            # Flow control for file playback: wait if ring buffer is already full
            if self._is_file:
                with self._buffer_lock:
                    is_full = len(self._ring_buffer) >= RING_BUFFER_CAPACITY
                if is_full:
                    self._frame_consumed_event.clear()
                    self._frame_consumed_event.wait(timeout=0.02)
                    continue

            # Regulate playback frame-rate when reading from a video file
            if self._is_file and self.target_fps > 0:
                frame_interval = 1.0 / self.target_fps
                elapsed = time.perf_counter() - last_frame_time
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                last_frame_time = time.perf_counter()

            ret, frame = self._cap.read()

            # Handle End Of Stream (EOS) or dropped frame
            if not ret or frame is None:
                if self._is_file and self.loop:
                    self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self._cap.read()
                    if not ret or frame is None:
                        self._fatal_error = CameraError(
                            "Failed to rewind video file on EOS",
                            details={"subcode": "CAMERA_EOS_FAILED"},
                        )
                        break
                elif not self._is_file:
                    self._dropped_frames += 1
                    consecutive_drops += 1
                    self._consecutive_drops = consecutive_drops
                    if consecutive_drops > MAX_TRANSIENT_DROPS:
                        # Attempt bounded device recovery
                        reopened = False
                        for attempt in range(5):
                            logger.warning(
                                "Camera device stream dropped; attempting recovery",
                                attempt=attempt + 1,
                                source=str(self.source),
                            )
                            time.sleep(0.2 * (attempt + 1))
                            try:
                                if self._cap:
                                    self._cap.release()
                                dev_idx = (
                                    int(self.source) if str(self.source).isdigit() else self.source
                                )
                                self._cap = cv2.VideoCapture(dev_idx)
                                if self._cap and self._cap.isOpened():
                                    self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
                                    self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
                                    self._cap.set(cv2.CAP_PROP_FPS, self.target_fps)
                                    ret_try, _ = self._cap.read()
                                    if ret_try:
                                        reopened = True
                                        consecutive_drops = 0
                                        self._consecutive_drops = 0
                                        logger.info("Camera device successfully reconnected")
                                        break
                            except Exception as rec_exc:
                                logger.debug("Camera recovery attempt failed", error=str(rec_exc))

                        if not reopened:
                            logger.warning(
                                "Camera reconnection pending; waiting before next retry",
                                source=str(self.source),
                            )
                            time.sleep(0.5)
                            consecutive_drops = 0
                        continue
                    time.sleep(0.01)
                    continue
                else:
                    self._eos_reached = True
                    self._is_active = False
                    self._frame_ready_event.set()
                    break

            consecutive_drops = 0
            self._consecutive_drops = 0
            h, w = frame.shape[:2]

            # Resize if dimensions differ significantly from targets
            if (w != self.target_width or h != self.target_height) and self.target_width > 0:
                frame = cv2.resize(frame, (self.target_width, self.target_height))
                h, w = self.target_height, self.target_width

            self._frame_index += 1
            now_utc = datetime.now(UTC)
            self._last_frame_time_utc = now_utc
            sensor_ns = time.time_ns()

            contract = FrameContract(
                camera_id=self.camera_id,
                frame_index=self._frame_index,
                resolution=Resolution(width=w, height=h),
                channels=3,
                pixel_format="BGR8",
                timestamp_utc=now_utc,
                timestamp_sensor_ns=sensor_ns,
            )

            with self._buffer_lock:
                self._ring_buffer.append((contract, frame))
                self._frame_ready_event.set()

        logger.debug("Capture worker thread exited", camera_id=self.camera_id)

    async def shutdown(self) -> None:
        """Safely signal capture thread to halt and release camera hardware handle."""
        self._is_active = False
        self._frame_ready_event.set()
        self._frame_consumed_event.set()

        if self._capture_thread and self._capture_thread.is_alive():
            await asyncio.to_thread(self._capture_thread.join, 2.0)
            self._capture_thread = None
            self._worker = None

        if self._cap:
            await asyncio.to_thread(self._cap.release)
            self._cap = None

        with self._buffer_lock:
            self._ring_buffer.clear()

        logger.info("Camera driver shut down safely", camera_id=self.camera_id)

    async def read_frame(self) -> tuple[FrameContract, np.ndarray[Any, Any]]:
        """Fetch latest frame buffer from bounded ring buffer."""
        if self._fatal_error:
            raise self._fatal_error

        if not self._is_active and not self._ring_buffer:
            if self._eos_reached:
                raise CameraError(
                    "Optical stream reached end-of-stream",
                    details={"subcode": "CAMERA_STREAM_ENDED"},
                )
            raise CameraError(
                "Cannot read frame: camera driver is not initialized",
                details={"subcode": "CAMERA_NOT_INITIALIZED"},
            )

        return await asyncio.to_thread(self._pop_frame_from_buffer, 2.0)

    def _pop_frame_from_buffer(
        self, timeout_s: float
    ) -> tuple[FrameContract, np.ndarray[Any, Any]]:
        """Block worker thread until next frame is retrieved from ring buffer."""
        if not self._frame_ready_event.wait(timeout=timeout_s):
            if self._fatal_error:
                raise self._fatal_error
            if self._eos_reached:
                raise CameraError(
                    "Optical stream reached end-of-stream",
                    details={"subcode": "CAMERA_STREAM_ENDED"},
                )
            raise CameraError(
                "Frame acquisition timed out waiting on ring buffer",
                details={"subcode": "CAMERA_TIMEOUT"},
            )

        with self._buffer_lock:
            if self._ring_buffer:
                item = self._ring_buffer.popleft()
                self._frame_consumed_event.set()
                if not self._ring_buffer and not self._eos_reached:
                    self._frame_ready_event.clear()
                return item

            if self._eos_reached:
                raise CameraError(
                    "Optical stream reached end-of-stream",
                    details={"subcode": "CAMERA_STREAM_ENDED"},
                )
            raise CameraError(
                "Ring buffer empty",
                details={"subcode": "CAMERA_BUFFER_EMPTY"},
            )

    def get_intrinsics(self) -> CameraIntrinsics:
        """Return optical calibration matrix and lens distortion coefficients."""
        fx = float(self.target_width) * 1.2
        fy = float(self.target_height) * 1.2
        cx = float(self.target_width) / 2.0
        cy = float(self.target_height) / 2.0
        return CameraIntrinsics(
            fx=fx,
            fy=fy,
            cx=cx,
            cy=cy,
            distortion_coeffs=[0.0, 0.0, 0.0, 0.0, 0.0],
        )
