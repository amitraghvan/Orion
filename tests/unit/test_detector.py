"""Unit tests for YOLOEdgeDetector running real edge inference."""

from pathlib import Path

import numpy as np
import pytest

from orion.core.exceptions import InferenceError
from orion_ai.detection.schemas import DetectionResult
from orion_ai.detection.yolo_detector import YOLOEdgeDetector


@pytest.mark.asyncio
@pytest.mark.unit
async def test_yolo_detector_inference() -> None:
    """Verify detector loads weights and runs inference on image buffer."""
    weights_path = Path("models/weights/yolo11n.pt")
    assert weights_path.exists(), "yolo11n.pt must exist for unit tests"

    detector = YOLOEdgeDetector(
        confidence_threshold=0.25,
        device="cpu",
    )
    assert not detector.is_loaded

    await detector.load(str(weights_path))
    assert detector.is_loaded

    # Create synthetic test frame (640x480 BGR)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[100:300, 100:300] = [200, 200, 200]

    result = await detector.detect(frame, frame_index=42)
    assert isinstance(result, DetectionResult)
    assert result.frame_index == 42
    assert result.inference_latency_ms > 0
    assert result.timestamp_sensor_ns > 0
    assert isinstance(result.detections, list)

    await detector.unload()
    assert not detector.is_loaded


@pytest.mark.asyncio
@pytest.mark.unit
async def test_yolo_detector_uninitialized_error() -> None:
    """Verify detector raises InferenceError when inference is called before initialization."""
    detector = YOLOEdgeDetector()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    with pytest.raises(InferenceError) as exc_info:
        await detector.detect(frame, frame_index=1)

    assert exc_info.value.code == "INFERENCE_ERROR"
    assert exc_info.value.details.get("subcode") == "DETECTOR_NOT_LOADED"
