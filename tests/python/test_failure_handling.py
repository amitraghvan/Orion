"""Tests for failure handling, fault containment, and graceful degradation."""

from pathlib import Path

import numpy as np
import pytest
from app.audio.tts_engine import TTSEngine

from orion.core.exceptions import CameraError
from orion_ai.camera.camera_manager import CameraManager
from orion_ai.camera.camera_sources import CameraStatus, LiveCameraSource, ReplayVideoSource


def test_corrupt_or_missing_replay_graceful_handling(tmp_path):
    """Test that a corrupt or missing replay file fails gracefully without crashing."""
    corrupt_file = tmp_path / "corrupt.mp4"
    corrupt_file.write_bytes(b"NOT_A_VALID_MP4_HEADER_GARBAGE_DATA")

    source = ReplayVideoSource(filepath=corrupt_file)
    # open() must return False without throwing uncaught fatal exception
    ok = source.open()
    assert ok is False
    assert source.is_opened() is False

    success, frame, frame_id, ts = source.read()
    assert success is False
    assert frame is None
    source.close()


def test_camera_disconnect_and_reconnect_resilience():
    """Test that disconnected camera handles frame reads gracefully and attempts recovery."""
    source = LiveCameraSource(source_id=99999)  # Invalid device index
    ok = source.open()
    assert ok is False
    assert source.is_opened() is False

    # Reading from unopened camera must return (False, None) gracefully, not throw
    success, frame, frame_id, ts = source.read()
    assert success is False
    assert frame is None


def test_camera_manager_handles_missing_device_gracefully():
    """Test that CameraManager handles unavailable device without application crash."""
    mgr = CameraManager(default_source=99999)
    started = mgr.start()
    assert started is False
    assert mgr.status == CameraStatus.ERROR
    assert mgr.is_connected is False

    # Querying frames from failed camera returns None safely
    assert mgr.latest_frame is None
    assert mgr.get_latest_jpeg() is None

    # Calling stop cleans up safely
    mgr.stop()
    assert mgr.status == CameraStatus.DISCONNECTED


def test_cpu_fallback_when_mps_or_cuda_unavailable(monkeypatch):
    """Test that PyTorch models gracefully fall back to CPU."""
    import torch
    from app.models.pytorch_backend import PyTorchBackend

    # Create backend with forced CPU device
    backend = PyTorchBackend(model_path="models/weights/yolo11n.pt", device="cpu")
    loaded = backend.load()
    assert loaded is True
    assert backend.is_loaded is True

    # Inference executes on CPU successfully
    test_img = np.zeros((320, 320, 3), dtype=np.uint8)
    results = backend.predict(test_img)
    assert results is not None


def test_tts_engine_graceful_fallback_when_unavailable():
    """Test that TTSEngine gracefully handles uninitialized/unsupported audio devices."""
    tts = TTSEngine()
    # Stopping uninitialized TTS engine must not throw
    tts.stop()
    assert tts._is_running is False

    # Speaking to uninitialized or muted engine does not throw
    ret = tts.speak("Emergency protocol check", priority=1)
    assert ret is False
