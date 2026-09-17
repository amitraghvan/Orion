"""Camera sources and frame buffer abstraction for ORION BAS AI Copilot.

Provides:
- CameraStatus enum (DISCONNECTED, CONNECTING, CONNECTED, PROCESSING, ERROR)
- FrameSource common abstract base class
- LiveCameraSource for physical webcam hardware
- ReplayVideoSource for BAS experiment recordings
- FrameBuffer for lock-free latest-frame access
"""

from __future__ import annotations

import os
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from enum import Enum
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from orion.core.logger import get_logger
from orion_ai.camera.schemas import FrameContract

logger = get_logger("orion_ai.camera.sources")

try:
    import orion_native  # type: ignore

    _HAS_NATIVE_ENGINE = True
except ImportError:
    _HAS_NATIVE_ENGINE = False


class CameraStatus(str, Enum):
    """Authoritative operational state of optical capture subsystem."""

    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    PROCESSING = "PROCESSING"
    ERROR = "ERROR"


class FrameSource(ABC):
    """Abstract interface for all frame acquisition providers."""

    def __init__(
        self,
        source_id: str | int,
        target_width: int = 1280,
        target_height: int = 720,
        target_fps: int = 30,
    ) -> None:
        self.source_id = str(source_id)
        self.target_width = target_width
        self.target_height = target_height
        self.target_fps = target_fps
        self._frame_id: int = 0

    @property
    @abstractmethod
    def is_file(self) -> bool:
        """Return whether the underlying source is a recorded video file."""
        raise NotImplementedError

    @abstractmethod
    def open(self) -> bool:
        """Open acquisition handle. Returns True if hardware/file opened successfully."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Release acquisition handle and close all underlying resources."""
        raise NotImplementedError

    @abstractmethod
    def is_opened(self) -> bool:
        """Return True if acquisition handle is active and open."""
        raise NotImplementedError

    @abstractmethod
    def read(self) -> tuple[bool, np.ndarray | None, int, float]:
        """Fetch next frame. Returns (success, frame_bgr, frame_id, timestamp_monotonic)."""
        raise NotImplementedError

    @abstractmethod
    def get_resolution(self) -> tuple[int, int]:
        """Return current frame dimensions (width, height)."""
        raise NotImplementedError


class LiveCameraSource(FrameSource):
    """Hardware webcam or RTSP stream acquisition source with reconnect resilience."""

    def __init__(
        self,
        source_id: str | int = 0,
        target_width: int = 1280,
        target_height: int = 720,
        target_fps: int = 30,
        enable_native: bool = False,
    ) -> None:
        super().__init__(source_id, target_width, target_height, target_fps)
        self.enable_native = enable_native
        self._cap: cv2.VideoCapture | None = None
        self._native_engine: Any = None
        self._use_native: bool = False
        self._consecutive_failures: int = 0
        self._lock = threading.RLock()
        self._actual_width: int = target_width
        self._actual_height: int = target_height

    @property
    def is_file(self) -> bool:
        return False

    def open(self) -> bool:
        with self._lock:
            self.close()

            # Attempt native C++ CameraEngine if requested
            if self.enable_native and _HAS_NATIVE_ENGINE:
                try:
                    engine = orion_native.CameraEngine()
                    if engine.open(
                        self.source_id, self.target_width, self.target_height, self.target_fps
                    ):
                        self._native_engine = engine
                        self._native_engine.start()
                        self._use_native = True
                        logger.info(
                            "LiveCameraSource using native C++ CameraEngine", source=self.source_id
                        )
                        return True
                except Exception as exc:
                    logger.warning(
                        "C++ CameraEngine open failed, falling back to OpenCV", error=str(exc)
                    )
                    self._use_native = False

            dev_idx = int(self.source_id) if self.source_id.isdigit() else self.source_id
            logger.info("Opening LiveCameraSource via OpenCV", device=dev_idx)

            # Platform-specific backend hints: AVFoundation on macOS
            if isinstance(dev_idx, int) and os.name != "nt":
                cap = cv2.VideoCapture(dev_idx, cv2.CAP_AVFOUNDATION)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(dev_idx)
            else:
                cap = cv2.VideoCapture(dev_idx)

            if not cap.isOpened():
                logger.error("LiveCameraSource could not open video capture", source=self.source_id)
                return False

            if isinstance(dev_idx, int):
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
                cap.set(cv2.CAP_PROP_FPS, self.target_fps)

            # Test-read one frame to verify hardware sensor is actually delivering pixels
            ret, test_frame = cap.read()
            if not ret or test_frame is None or test_frame.size == 0:
                logger.error(
                    "LiveCameraSource opened handle but failed test frame read",
                    source=self.source_id,
                )
                cap.release()
                return False

            h, w = test_frame.shape[:2]
            self._actual_width = w
            self._actual_height = h
            self._cap = cap
            self._consecutive_failures = 0
            logger.info(
                "LiveCameraSource successfully opened and verified",
                source=self.source_id,
                dimensions=f"{w}x{h}",
            )
            return True

    def close(self) -> None:
        with self._lock:
            if self._native_engine is not None:
                try:
                    self._native_engine.stop()
                    self._native_engine.close()
                except Exception:
                    pass
                self._native_engine = None

            if self._cap is not None:
                try:
                    self._cap.release()
                except Exception:
                    pass
                self._cap = None
            self._use_native = False

    def is_opened(self) -> bool:
        with self._lock:
            if self._use_native and self._native_engine is not None:
                return True
            return self._cap is not None and self._cap.isOpened()

    def read(self) -> tuple[bool, np.ndarray | None, int, float]:
        with self._lock:
            now = time.monotonic()
            if self._use_native and self._native_engine is not None:
                native_frame = self._native_engine.read_frame(timeout_ms=100)
                if native_frame is not None:
                    self._frame_id += 1
                    self._consecutive_failures = 0
                    return True, native_frame.to_numpy(), self._frame_id, now
                self._consecutive_failures += 1
                return False, None, self._frame_id, now

            if self._cap is None or not self._cap.isOpened():
                return False, None, self._frame_id, now

            ret, frame = self._cap.read()
            if ret and frame is not None and frame.size > 0:
                self._frame_id += 1
                self._consecutive_failures = 0
                return True, frame, self._frame_id, now

            self._consecutive_failures += 1
            # Reconnect attempt if continuous drops exceed threshold
            if self._consecutive_failures > 30:
                logger.warning(
                    "LiveCameraSource experiencing sustained drops, attempting reconnect",
                    failures=self._consecutive_failures,
                )
                self.open()

            return False, None, self._frame_id, now

    def get_resolution(self) -> tuple[int, int]:
        with self._lock:
            return self._actual_width, self._actual_height


class ReplayVideoSource(FrameSource):
    """Replay video source for real BAS experiment recordings with natural frame pacing."""

    def __init__(
        self,
        filepath: str | Path,
        target_width: int = 1280,
        target_height: int = 720,
        target_fps: int = 30,
        loop: bool = True,
    ) -> None:
        p = Path(filepath).resolve()
        super().__init__(str(p), target_width, target_height, target_fps)
        self.filepath = p
        self.loop = loop
        self._cap: cv2.VideoCapture | None = None
        self._lock = threading.RLock()
        self._video_fps: float = float(target_fps)
        self._actual_width: int = target_width
        self._actual_height: int = target_height
        self._last_read_time: float = 0.0

    @property
    def is_file(self) -> bool:
        return True

    def open(self) -> bool:
        with self._lock:
            self.close()
            if not self.filepath.is_file():
                logger.error("ReplayVideoSource file not found", path=str(self.filepath))
                return False

            cap = cv2.VideoCapture(str(self.filepath))
            if not cap.isOpened():
                logger.error("ReplayVideoSource failed to open video file", path=str(self.filepath))
                return False

            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps and fps > 0:
                self._video_fps = fps
            else:
                self._video_fps = float(self.target_fps)

            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self._actual_width = w if w > 0 else self.target_width
            self._actual_height = h if h > 0 else self.target_height

            self._cap = cap
            self._frame_id = 0
            self._last_read_time = time.monotonic()
            logger.info(
                "ReplayVideoSource opened successfully",
                path=str(self.filepath),
                video_fps=self._video_fps,
                resolution=f"{self._actual_width}x{self._actual_height}",
            )
            return True

    def close(self) -> None:
        with self._lock:
            if self._cap is not None:
                try:
                    self._cap.release()
                except Exception:
                    pass
                self._cap = None

    def is_opened(self) -> bool:
        with self._lock:
            return self._cap is not None and self._cap.isOpened()

    def read(self) -> tuple[bool, np.ndarray | None, int, float]:
        with self._lock:
            now = time.monotonic()
            if self._cap is None or not self._cap.isOpened():
                return False, None, self._frame_id, now

            # Pacing: regulate replay playback to match video FPS
            interval = 1.0 / max(self._video_fps, 1.0)
            elapsed = now - self._last_read_time
            sleep_needed = interval - elapsed
            if sleep_needed > 0:
                time.sleep(sleep_needed)
            self._last_read_time = time.monotonic()

            ret, frame = self._cap.read()
            if not ret or frame is None:
                if self.loop:
                    # Rewind to start
                    self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self._cap.read()
                    if not ret or frame is None:
                        return False, None, self._frame_id, time.monotonic()
                else:
                    return False, None, self._frame_id, time.monotonic()

            self._frame_id += 1
            return True, frame, self._frame_id, self._last_read_time

    def get_resolution(self) -> tuple[int, int]:
        with self._lock:
            return self._actual_width, self._actual_height


class FrameBuffer:
    """Thread-safe bounded latest-frame buffer isolating capture from consumers.

    Enforces:
    - Bounded queue (maxlen=2) to prevent unbounded latency.
    - Zero-copy / atomic swap for latest BGR and JPEG bytes.
    - Accurate dropped frames and frame counter tracking.
    """

    def __init__(self, capacity: int = 2) -> None:
        self.capacity = max(capacity, 1)
        self._lock = threading.RLock()
        self._buffer: deque[tuple[FrameContract, np.ndarray]] = deque(maxlen=self.capacity)
        self._latest_bgr: np.ndarray | None = None
        self._latest_jpeg: bytes | None = None
        self._latest_contract: FrameContract | None = None
        self._frame_ready_event = threading.Event()
        self._frames_captured: int = 0
        self._frames_dropped: int = 0
        self._last_push_time: float = 0.0

    def push(self, frame_bgr: np.ndarray, contract: FrameContract) -> None:
        """Push newly acquired frame into the buffer, replacing stale frames."""
        with self._lock:
            if len(self._buffer) >= self.capacity:
                self._frames_dropped += 1

            self._buffer.append((contract, frame_bgr))
            self._latest_bgr = frame_bgr
            self._latest_contract = contract
            self._frames_captured += 1
            self._last_push_time = time.monotonic()

            # Pre-encode JPEG for zero-latency HTTP frame streaming
            try:
                h, w = frame_bgr.shape[:2]
                if w > 640:
                    scale = 640.0 / w
                    small = cv2.resize(
                        frame_bgr, (640, int(h * scale)), interpolation=cv2.INTER_AREA
                    )
                else:
                    small = frame_bgr
                ok, enc = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ok:
                    self._latest_jpeg = enc.tobytes()
            except Exception:
                pass

            self._frame_ready_event.set()

    def get_latest(self) -> tuple[np.ndarray | None, FrameContract | None]:
        """Fetch the newest frame atomically without blocking."""
        with self._lock:
            if self._latest_bgr is not None:
                return self._latest_bgr.copy(), self._latest_contract
            return None, None

    def get_latest_jpeg(self) -> bytes | None:
        """Fetch pre-encoded JPEG bytes of latest frame for HTTP / WebSocket transport."""
        with self._lock:
            return self._latest_jpeg

    def wait_for_frame(self, timeout_s: float = 1.0) -> bool:
        """Wait until a new frame has arrived."""
        return self._frame_ready_event.wait(timeout=timeout_s)

    def pop_frame(self, timeout_s: float = 1.0) -> tuple[FrameContract, np.ndarray] | None:
        """Pop next frame for sequential consumers (blocking up to timeout)."""
        if not self._frame_ready_event.wait(timeout=timeout_s):
            return None

        with self._lock:
            if self._buffer:
                item = self._buffer.popleft()
                if not self._buffer:
                    self._frame_ready_event.clear()
                return item
            self._frame_ready_event.clear()
            return None

    def clear(self) -> None:
        """Reset buffer state."""
        with self._lock:
            self._buffer.clear()
            self._latest_bgr = None
            self._latest_jpeg = None
            self._latest_contract = None
            self._frame_ready_event.clear()

    @property
    def frames_captured(self) -> int:
        with self._lock:
            return self._frames_captured

    @property
    def frames_dropped(self) -> int:
        with self._lock:
            return self._frames_dropped

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._buffer)
