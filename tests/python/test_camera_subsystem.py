"""Tests for authoritative CameraManager, FrameSource, and FrameBuffer subsystems."""

import time
from pathlib import Path

import numpy as np
import pytest

from orion_ai.camera.camera_manager import CameraManager, authoritative_camera_manager
from orion_ai.camera.camera_sources import (
    CameraStatus,
    FrameBuffer,
    LiveCameraSource,
    ReplayVideoSource,
)
from orion_ai.camera.schemas import FrameContract, Resolution


def test_frame_buffer_bounded_operations():
    """Verify FrameBuffer bounded ring behavior, dropped frames tracking, and latest frame access."""
    buffer = FrameBuffer(capacity=2)
    assert buffer.size == 0
    assert buffer.frames_captured == 0
    assert buffer.frames_dropped == 0

    frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
    contract1 = FrameContract(
        camera_id="test_cam",
        frame_index=1,
        resolution=Resolution(width=640, height=480),
        timestamp_sensor_ns=time.time_ns(),
    )
    buffer.push(frame1, contract1)
    assert buffer.size == 1
    assert buffer.frames_captured == 1
    assert buffer.frames_dropped == 0

    frame2 = np.ones((480, 640, 3), dtype=np.uint8)
    contract2 = FrameContract(
        camera_id="test_cam",
        frame_index=2,
        resolution=Resolution(width=640, height=480),
        timestamp_sensor_ns=time.time_ns(),
    )
    buffer.push(frame2, contract2)
    assert buffer.size == 2
    assert buffer.frames_captured == 2
    assert buffer.frames_dropped == 0

    # Pushing 3rd frame must drop oldest frame without unbounded growth
    frame3 = np.full((480, 640, 3), 2, dtype=np.uint8)
    contract3 = FrameContract(
        camera_id="test_cam",
        frame_index=3,
        resolution=Resolution(width=640, height=480),
        timestamp_sensor_ns=time.time_ns(),
    )
    buffer.push(frame3, contract3)
    assert buffer.size == 2
    assert buffer.frames_captured == 3
    assert buffer.frames_dropped == 1

    # Atomic latest frame verification
    latest_frame, latest_contract = buffer.get_latest()
    assert latest_frame is not None
    assert latest_contract is not None
    assert latest_contract.frame_index == 3

    # Pre-encoded JPEG verification
    jpeg_bytes = buffer.get_latest_jpeg()
    assert jpeg_bytes is not None
    assert len(jpeg_bytes) > 0
    assert jpeg_bytes.startswith(b"\xff\xd8")  # Valid JPEG SOI marker

    # Pop frames
    item = buffer.pop_frame(timeout_s=0.1)
    assert item is not None
    assert item[0].frame_index == 2  # Frame 2 was not dropped, Frame 1 was dropped

    buffer.clear()
    assert buffer.size == 0
    assert buffer.get_latest()[0] is None
    assert buffer.get_latest_jpeg() is None


def test_replay_video_source():
    """Verify ReplayVideoSource opens real recording and streams valid frames."""
    sample_file = Path("assets/sample_replay.mp4").resolve()
    assert sample_file.is_file(), "assets/sample_replay.mp4 must exist for replay testing"

    source = ReplayVideoSource(filepath=sample_file, target_width=640, target_height=480, target_fps=30)
    assert source.is_file is True
    assert source.is_opened() is False

    ok = source.open()
    assert ok is True
    assert source.is_opened() is True

    # Read frames
    success, frame, frame_id, ts = source.read()
    assert success is True
    assert frame is not None
    assert isinstance(frame, np.ndarray)
    assert frame.shape[2] == 3
    assert frame_id == 1
    assert ts > 0.0

    # Read second frame
    success, frame, frame_id, ts = source.read()
    assert success is True
    assert frame_id == 2

    source.close()
    assert source.is_opened() is False


def test_camera_manager_truthful_status():
    """Verify CameraManager truthfully reports DISCONNECTED when not active."""
    mgr = CameraManager(default_source=999)  # Non-existent device
    assert mgr.status == CameraStatus.DISCONNECTED
    assert mgr.is_connected is False
    assert mgr.is_active is False
    assert mgr.actual_fps == 0.0
    assert mgr.latest_frame is None
    assert mgr.get_latest_jpeg() is None

    # Opening non-existent device must report ERROR truthfully, never CONNECTED
    ok = mgr.start()
    assert ok is False
    assert mgr.status == CameraStatus.ERROR
    assert mgr.is_connected is False
    assert mgr.last_error is not None
    mgr.stop()
    assert mgr.status == CameraStatus.DISCONNECTED


def test_camera_manager_with_replay():
    """Verify CameraManager running with real video file source."""
    sample_file = Path("assets/sample_replay.mp4").resolve()
    mgr = CameraManager(default_source=str(sample_file), width=640, height=480, fps=30)

    ok = mgr.start()
    assert ok is True
    assert mgr.is_connected is True
    assert mgr.status in (CameraStatus.CONNECTED, CameraStatus.PROCESSING)

    # Wait briefly for capture thread to populate buffer
    for _ in range(20):
        if mgr.latest_frame is not None:
            break
        time.sleep(0.05)

    assert mgr.latest_frame is not None
    assert mgr.get_latest_jpeg() is not None
    assert mgr.frames_captured > 0

    # Health report
    rep = mgr.get_health_report()
    assert rep.subsystem_id == "camera"
    assert rep.status.value in ("HEALTHY", "DEGRADED")
    assert rep.metrics["frames_captured"] > 0

    mgr.stop()
    assert mgr.is_connected is False
    assert mgr.status == CameraStatus.DISCONNECTED
