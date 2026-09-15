"""Unit tests for dedicated camera capture worker thread and bounded ring buffer."""

from pathlib import Path

import pytest

from orion_ai.camera.opencv_driver import OpenCVCameraDriver


@pytest.mark.asyncio
@pytest.mark.unit
async def test_camera_capture_worker_thread_lifecycle() -> None:
    """Verify capture worker thread is spawned on init and cleanly stopped on shutdown."""
    video_path = Path("assets/sample_replay.mp4")
    assert video_path.exists()

    driver = OpenCVCameraDriver(
        source=str(video_path),
        camera_id="bas_worker_test",
        target_fps=0,  # Uncapped for fast test execution
        width=640,
        height=480,
        loop=True,
    )

    await driver.initialize()
    assert driver.is_active
    assert driver._worker is not None
    assert driver._worker.is_alive()

    # Read several consecutive frames from bounded ring buffer
    for expected_idx in range(1, 6):
        contract, frame = await driver.read_frame()
        assert contract.frame_index >= expected_idx
        assert frame.shape == (480, 640, 3)

    # Shutdown should terminate worker thread
    worker = driver._worker
    await driver.shutdown()
    assert not driver.is_active
    assert not worker.is_alive()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_camera_capture_ring_buffer_bounded_capacity() -> None:
    """Verify that internal buffer is bounded with deque maxlen=2."""
    video_path = Path("assets/sample_replay.mp4")
    driver = OpenCVCameraDriver(
        source=str(video_path),
        camera_id="bas_ring_test",
        target_fps=60,
        loop=True,
    )
    await driver.initialize()
    try:
        # Buffer maxlen must be 2
        assert driver._buffer.maxlen == 2
        contract, frame = await driver.read_frame()
        assert contract is not None
        assert frame is not None
    finally:
        await driver.shutdown()
