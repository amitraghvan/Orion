"""Unit tests for YOLOPoseEstimator extracting 17-point COCO whole-body keypoints."""

from pathlib import Path

import numpy as np
import pytest

from orion.core.exceptions import InferenceError
from orion_ai.pose.schemas import PoseEstimationResult
from orion_ai.pose.yolo_pose import YOLOPoseEstimator


@pytest.mark.asyncio
@pytest.mark.unit
async def test_yolo_pose_estimator_inference() -> None:
    """Verify pose estimator loads weights and runs inference on image buffer."""
    weights_path = Path("models/weights/yolo11n-pose.pt")
    assert weights_path.exists(), "yolo11n-pose.pt must exist for unit tests"

    estimator = YOLOPoseEstimator(
        confidence_threshold=0.25,
        device="cpu",
    )
    assert not estimator.is_loaded

    await estimator.load(str(weights_path))
    assert estimator.is_loaded

    # Create synthetic test frame (640x480 BGR)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[100:300, 100:300] = [180, 180, 180]

    result = await estimator.estimate(frame)
    assert isinstance(result, PoseEstimationResult)
    assert result.inference_time_ms > 0
    assert isinstance(result.poses, list)

    await estimator.unload()
    assert not estimator.is_loaded


@pytest.mark.asyncio
@pytest.mark.unit
async def test_yolo_pose_uninitialized_error() -> None:
    """Verify pose estimator raises InferenceError when called before initialization."""
    estimator = YOLOPoseEstimator()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    with pytest.raises(InferenceError) as exc_info:
        await estimator.estimate(frame)

    assert exc_info.value.code == "INFERENCE_ERROR"
    assert exc_info.value.details.get("subcode") == "POSE_NOT_LOADED"
