"""Unit tests for OpenCVCameraDriver optical ingestion and video replay."""

from pathlib import Path

import pytest

from orion.core.exceptions import CameraError
from orion_ai.camera.opencv_driver import OpenCVCameraDriver


@pytest.mark.asyncio
@pytest.mark.unit
async def test_camera_driver_video_replay() -> None:
    """Verify camera driver correctly ingests frames from a video file."""
    video_path = Path("assets/sample_replay.mp4")
    assert video_path.exists(), "Sample video assets/sample_replay.mp4 must exist"

    driver = OpenCVCameraDriver(
        source=str(video_path),
        camera_id="bas_cam_test",
        target_fps=60,
        width=640,
        height=480,
        loop=True,
    )

    await driver.initialize()
    assert driver.is_active

    contract, frame = await driver.read_frame()
    assert contract.camera_id == "bas_cam_test"
    assert contract.frame_index == 1
    assert contract.resolution.width == 640
    assert contract.resolution.height == 480
    assert frame.shape == (480, 640, 3)

    # Intrinsics
    intrinsics = driver.get_intrinsics()
    assert intrinsics.fx > 0
    assert intrinsics.fy > 0

    await driver.shutdown()
    assert not driver.is_active


@pytest.mark.asyncio
@pytest.mark.unit
async def test_camera_driver_file_not_found() -> None:
    """Verify camera driver raises CameraError on nonexistent file."""
    driver = OpenCVCameraDriver(source="assets/nonexistent_video.mp4")
    with pytest.raises(CameraError) as exc_info:
        await driver.initialize()
    assert exc_info.value.code == "CAMERA_ERROR"
    assert exc_info.value.details.get("subcode") == "CAMERA_FILE_NOT_FOUND"
