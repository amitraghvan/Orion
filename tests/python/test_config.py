"""Unit tests for ORION desktop configuration management."""

from pathlib import Path

import pytest
from app.core.config import (
    CameraConfig,
    ModelsConfig,
    OrionConfig,
    SystemConfig,
    get_config,
    load_config,
    set_config,
)


def test_default_orion_config():
    """Verify default OrionConfig loads all configurations without errors."""
    cfg = get_config()
    assert isinstance(cfg, OrionConfig)
    assert isinstance(cfg.system, SystemConfig)
    assert cfg.system.station_id.startswith("BAS")
    assert cfg.system.glovebox_id == "GB-01"


def test_camera_config():
    """Verify CameraConfig parameters."""
    cfg = get_config()
    cam = cfg.camera
    assert isinstance(cam, CameraConfig)
    assert cam.width > 0
    assert cam.height > 0
    assert cam.fps > 0
    assert cam.buffer_size >= 1


def test_models_config():
    """Verify ModelsConfig contains required models and thresholds."""
    cfg = get_config()
    models = cfg.models
    assert isinstance(models, ModelsConfig)
    assert models.detection.path != ""
    assert models.pose.path != ""
    assert models.activity.path != ""
    assert 0.0 <= models.activity.confidence <= 1.0


def test_custom_config_save_and_load(tmp_path: Path):
    """Verify loading custom configuration from a custom directory."""
    custom_yaml = tmp_path / "custom_config.yaml"
    custom_cfg = OrionConfig()
    custom_cfg.system.station_id = "BAS-TEST-BENCH"
    custom_cfg.camera.width = 1920
    custom_cfg.camera.height = 1080
    custom_cfg.save_yaml(custom_yaml)

    loaded = load_config(custom_yaml)
    assert loaded.system.station_id == "BAS-TEST-BENCH"
    assert loaded.camera.width == 1920
    assert loaded.camera.height == 1080
