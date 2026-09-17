"""Unit tests for CanonicalFeatureTransformer verifying parity between dataset generation and runtime inference."""

import numpy as np
import pytest
from orion_ai.activity.feature_transformer import CanonicalFeatureTransformer, canonical_transformer
from app.intelligence.temporal_engine import TemporalHAREngine


def test_pixel_to_normalized_coordinate():
    """Verify pixel coordinates map accurately to [0.0, 1.0] range based on frame dimensions."""
    transformer = CanonicalFeatureTransformer(num_joints=17)
    kpts = np.zeros((17, 3), dtype=np.float32)
    # Nose at (320, 240) in 640x480 frame
    kpts[0] = [320.0, 240.0, 0.9]
    # Left wrist at (640, 480)
    kpts[9] = [640.0, 480.0, 0.85]

    feat = transformer.transform_frame(kpts, frame_width=640.0, frame_height=480.0, interaction_score=0.75)
    assert feat.shape == (4, 17)

    # Nose x, y normalized
    assert pytest.approx(feat[0, 0], abs=1e-4) == 0.5
    assert pytest.approx(feat[1, 0], abs=1e-4) == 0.5
    assert pytest.approx(feat[2, 0], abs=1e-4) == 0.9

    # Left wrist x, y normalized
    assert pytest.approx(feat[0, 9], abs=1e-4) == 1.0
    assert pytest.approx(feat[1, 9], abs=1e-4) == 1.0
    assert pytest.approx(feat[2, 9], abs=1e-4) == 0.85
    # Interaction on wrist joint 9
    assert pytest.approx(feat[3, 9], abs=1e-4) == 0.75


def test_channel_order_and_dimensions():
    """Verify feature channel order: [x_norm, y_norm, confidence, interaction] and shape (4, 17)."""
    transformer = CanonicalFeatureTransformer(num_joints=17)
    kpts = np.random.uniform(low=50.0, high=500.0, size=(17, 3)).astype(np.float32)
    kpts[:, 2] = np.random.uniform(0.3, 0.95, size=17)

    feat = transformer.transform_frame(kpts, frame_width=1280.0, frame_height=720.0, interaction_score=0.6)
    assert feat.shape == (4, 17)
    assert feat.dtype == np.float32

    # Check non-negative and bounded
    assert np.all(feat >= 0.0)
    assert np.all(feat <= 1.0)

    # Interaction channels: 7, 8, 9, 10 must be 0.6; other joints 0.0
    for j in [7, 8, 9, 10]:
        assert pytest.approx(feat[3, j], abs=1e-4) == 0.6
    for j in [0, 1, 2, 3, 4, 5, 6, 11, 12, 13, 14, 15, 16]:
        assert pytest.approx(feat[3, j], abs=1e-4) == 0.0


def test_runtime_temporal_engine_buffer_layout():
    """Verify TemporalHAREngine buffers canonical (4, 17) frames and outputs (1, 4, 32, 17)."""
    engine = TemporalHAREngine(window_size=32, num_joints=17)
    assert not engine.is_buffer_full()

    # Push 32 frames of synthetic keypoints
    for i in range(32):
        kpts = np.full((17, 3), fill_value=(i + 1) * 10.0, dtype=np.float32)
        kpts[:, 2] = 0.9
        engine.push_frame_keypoints(kpts, frame_width=640.0, frame_height=480.0, interaction_score=0.5)

    assert engine.is_buffer_full()

    # Build sequence
    stacked = np.stack(list(engine._keypoint_buffer), axis=1)  # (4, 32, 17)
    tensor = np.expand_dims(stacked, axis=0).astype(np.float32)  # (1, 4, 32, 17)

    assert tensor.shape == (1, 4, 32, 17)
    # Validate tensor invariant
    canonical_transformer.validate_tensor(tensor)


def test_parity_between_direct_and_engine_features():
    """Verify identical features produced between CanonicalFeatureTransformer and TemporalHAREngine."""
    engine = TemporalHAREngine(window_size=32, num_joints=17)
    transformer = CanonicalFeatureTransformer(num_joints=17)

    kpts = np.ones((17, 3), dtype=np.float32) * 100.0
    kpts[:, 2] = 0.88

    direct_feat = transformer.transform_frame(kpts, frame_width=640.0, frame_height=480.0, interaction_score=0.45)
    engine.push_frame_keypoints(kpts, frame_width=640.0, frame_height=480.0, interaction_score=0.45)
    engine_feat = engine._keypoint_buffer[-1]

    np.testing.assert_allclose(direct_feat, engine_feat, rtol=1e-5, atol=1e-5)


def test_tensor_validation_assertions():
    """Verify validator catches invalid shapes and out-of-bounds values."""
    # Invalid channel count
    invalid_channels = np.zeros((1, 3, 32, 17), dtype=np.float32)
    with pytest.raises(AssertionError, match="Expected 4 channels"):
        CanonicalFeatureTransformer.validate_tensor(invalid_channels)

    # Invalid temporal length
    invalid_time = np.zeros((1, 4, 16, 17), dtype=np.float32)
    with pytest.raises(AssertionError, match="Expected 32 temporal frames"):
        CanonicalFeatureTransformer.validate_tensor(invalid_time)

    # Value out of bounds (> 1.01)
    unnormalized = np.full((1, 4, 32, 17), fill_value=250.0, dtype=np.float32)
    with pytest.raises(AssertionError, match="exceeds normalized range"):
        CanonicalFeatureTransformer.validate_tensor(unnormalized)
