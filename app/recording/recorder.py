"""Threaded local video recorder with background frame writing queue."""

from __future__ import annotations

import queue
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.core.config import get_config
from app.core.logging import get_logger
from app.core.state_manager import state_manager
from app.recording.storage_manager import storage_manager

logger = get_logger("app.recording.recorder")

try:
    import orion_native
    _HAS_NATIVE_RECORDER = True
except ImportError:
    _HAS_NATIVE_RECORDER = False


class ExperimentRecorder:
    """Asynchronously records mission video sessions to MP4 without degrading perception FPS."""

    def __init__(self) -> None:
        self._is_recording = False
        self._frame_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=120)
        self._worker_thread: threading.Thread | None = None
        self._lock = threading.RLock()

        self._session_dir: Path | None = None
        self._video_path: Path | None = None
        self._experiment_id: str = ""
        self._run_id: str = ""
        self._start_time: str = ""
        self._start_mono: float = 0.0
        self._width: int = 1280
        self._height: int = 720
        self._fps: int = 30
        self._frames_written: int = 0

        self._cv_writer: cv2.VideoWriter | None = None

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._is_recording

    @property
    def session_dir(self) -> Path | None:
        with self._lock:
            return self._session_dir

    @property
    def video_path(self) -> Path | None:
        with self._lock:
            return self._video_path

    def start_recording(self, experiment_id: str, run_id: str, width: int = 1280, height: int = 720, fps: int = 30) -> bool:
        """Commence background video recording for experiment session."""
        with self._lock:
            if self._is_recording:
                return True

            cfg = get_config()
            if not cfg.recording.enabled:
                logger.info("Recording is disabled in configuration.")
                return False

            self._experiment_id = experiment_id
            self._run_id = run_id
            self._width = width
            self._height = height
            self._fps = fps
            self._frames_written = 0
            self._start_time = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
            self._start_mono = time.monotonic()

            self._session_dir = storage_manager.create_session_directory(experiment_id, run_id)
            self._video_path = self._session_dir / "experiment.mp4"

            fourcc = cv2.VideoWriter_fourcc(*cfg.recording.codec)
            self._cv_writer = cv2.VideoWriter(str(self._video_path), fourcc, self._fps, (self._width, self._height))

            if not self._cv_writer.isOpened():
                # Try fallback mp4v or avc1
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                self._cv_writer = cv2.VideoWriter(str(self._video_path), fourcc, self._fps, (self._width, self._height))

            self._is_recording = True
            state_manager.set_recording(True)

            self._worker_thread = threading.Thread(target=self._write_worker, name="RecorderWorkerThread", daemon=True)
            self._worker_thread.start()
            logger.info("Started session recording", output=str(self._video_path))
            return True

    def push_frame(self, frame_bgr: np.ndarray) -> None:
        """Push a frame to the recording queue. Drops frame if queue is congested."""
        if not self._is_recording:
            return
        try:
            self._frame_queue.put_nowait(frame_bgr)
        except queue.Full:
            pass  # Drop frame to preserve real-time stability

    def stop_recording(self, events: list[dict[str, Any]] | None = None, timeline: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
        """Finalize video container and write metadata manifests."""
        with self._lock:
            if not self._is_recording:
                return None
            self._is_recording = False
            state_manager.set_recording(False)

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=3.0)

        duration = time.monotonic() - self._start_mono
        end_time = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

        metadata = {
            "experiment_id": self._experiment_id,
            "run_id": self._run_id,
            "start_time": self._start_time,
            "end_time": end_time,
            "duration_seconds": round(duration, 1),
            "width": self._width,
            "height": self._height,
            "fps": self._fps,
            "total_frames_recorded": self._frames_written,
            "video_file": "experiment.mp4",
        }

        if self._session_dir is not None:
            storage_manager.write_metadata(self._session_dir, metadata)
            if events:
                storage_manager.write_events(self._session_dir, events)
            if timeline:
                storage_manager.write_timeline_log(self._session_dir, timeline)

        logger.info("Finalized experiment recording", duration=round(duration, 1), frames=self._frames_written)
        return metadata

    def _write_worker(self) -> None:
        while self._is_recording or not self._frame_queue.empty():
            try:
                frame = self._frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if self._cv_writer is not None and self._cv_writer.isOpened():
                # Resize if frame dimensions differ from container
                if frame.shape[1] != self._width or frame.shape[0] != self._height:
                    frame = cv2.resize(frame, (self._width, self._height))
                self._cv_writer.write(frame)
                self._frames_written += 1

            self._frame_queue.task_done()

        if self._cv_writer is not None:
            self._cv_writer.release()
            self._cv_writer = None


# Global recorder singleton
experiment_recorder = ExperimentRecorder()
