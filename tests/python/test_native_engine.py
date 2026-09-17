"""Unit tests for the C++ orion_native pybind11 module."""

import numpy as np
import pytest

try:
    import orion_native
    HAS_ORION_NATIVE = True
except ImportError:
    HAS_ORION_NATIVE = False


@pytest.mark.skipif(not HAS_ORION_NATIVE, reason="orion_native C++ extension not compiled")
def test_orion_native_module_import():
    assert orion_native is not None
    assert hasattr(orion_native, "CameraEngine")
    assert hasattr(orion_native, "VideoProcessor")
    assert hasattr(orion_native, "ObjectTracker")
    assert hasattr(orion_native, "FrameData")
    assert hasattr(orion_native, "TrackedBBox")


@pytest.mark.skipif(not HAS_ORION_NATIVE, reason="orion_native C++ extension not compiled")
def test_video_processor_letterbox():
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame_data = orion_native.FrameData()
    frame_data.from_numpy(dummy_frame, 1, 1000)

    # Preprocess to 640x640 letterbox
    res = orion_native.VideoProcessor.letterbox(frame_data, 640, 640)
    assert res is not None
    assert res.processed_frame.width == 640
    assert res.processed_frame.height == 640
    assert res.scale > 0.0

    # Test CHW tensor conversion
    chw = orion_native.VideoProcessor.to_chw_tensor(res.processed_frame, True)
    assert isinstance(chw, np.ndarray)
    assert chw.shape == (3, 640, 640)
    assert chw.dtype == np.float32


@pytest.mark.skipif(not HAS_ORION_NATIVE, reason="orion_native C++ extension not compiled")
def test_object_tracker():
    tracker = orion_native.ObjectTracker(0.3, 30, 1)
    assert tracker is not None

    # Update with TrackedBBox
    bbox = orion_native.TrackedBBox()
    bbox.track_id = 1
    bbox.class_id = 0
    bbox.class_name = "test_box"
    bbox.confidence = 0.95
    bbox.x1 = 100.0
    bbox.y1 = 100.0
    bbox.x2 = 200.0
    bbox.y2 = 200.0

    tracks = tracker.update([bbox])
    assert isinstance(tracks, list)
    assert len(tracks) == 1
    assert tracks[0].track_id == 1


@pytest.mark.skipif(not HAS_ORION_NATIVE, reason="orion_native C++ extension not compiled")
def test_camera_engine_instantiation():
    cam = orion_native.CameraEngine()
    assert cam is not None
    assert cam.is_open() is False
    assert cam.is_running() is False
