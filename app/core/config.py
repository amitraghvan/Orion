"""Hierarchical application configuration loaded from YAML with Pydantic validation."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from app.core.exceptions import ConfigurationError
from app.core.paths import paths


class SystemConfig(BaseModel):
    """System-wide operational parameters."""

    station_id: str = "BAS-EXP-WORKSTATION-01"
    station_module: str = "BAS-SCIENCE-NODE-1"
    glovebox_id: str = "GB-01"
    mode: Literal["offline", "demo"] = "offline"
    performance_mode: Literal["balanced", "performance"] = "balanced"
    device: Literal["auto", "cpu", "mps", "cuda", "tensorrt"] = "auto"
    enable_cpp_engine: bool = True


class CameraConfig(BaseModel):
    """Optical video sensor acquisition configuration."""

    camera_id: str = "CAM01"
    source: str = "0"
    width: int = Field(default=1280, ge=320)
    height: int = Field(default=720, ge=240)
    fps: int = Field(default=30, ge=1, le=120)
    auto_reconnect: bool = True
    reconnect_interval_seconds: float = 2.0
    buffer_size: int = Field(default=5, ge=1, le=30)
    loop_video_files: bool = True


class ModelItemConfig(BaseModel):
    """Individual AI model parameters."""

    backend: Literal["auto", "pytorch", "onnx", "tensorrt"] = "auto"
    path: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    device: Literal["auto", "cpu", "mps", "cuda"] = "auto"
    enabled: bool = True


class ModelsConfig(BaseModel):
    """AI perception models registry."""

    detection: ModelItemConfig = Field(
        default_factory=lambda: ModelItemConfig(
            path="models/weights/yolo11n.pt",
            confidence=0.25,
        )
    )
    pose: ModelItemConfig = Field(
        default_factory=lambda: ModelItemConfig(
            path="models/weights/yolo11n-pose.pt",
            confidence=0.25,
        )
    )
    activity: ModelItemConfig = Field(
        default_factory=lambda: ModelItemConfig(
            path="models/bas_experiment/best.pt",
            confidence=0.65,
        )
    )
    window_size: int = Field(default=32, ge=8, le=128)
    entropy_threshold: float = Field(default=1.40, ge=0.5)


class AudioConfig(BaseModel):
    """Acoustic annunciations and offline TTS configuration."""

    voice_enabled: bool = True
    volume: float = Field(default=1.0, ge=0.0, le=1.0)
    rate: int = Field(default=175, ge=50, le=400)
    cooldown_seconds: float = Field(default=3.0, ge=0.5)
    chime_enabled: bool = True


class RecordingConfig(BaseModel):
    """Local mission session recording parameters."""

    enabled: bool = True
    output_dir: str = "recordings"
    codec: str = "mp4v"
    record_fps: int = 30
    save_raw_video: bool = True
    save_events_log: bool = True


class StreamingConfig(BaseModel):
    """Decoupled IP network video streaming parameters."""

    enabled: bool = False
    mode: str = "udp_unicast"  # "udp_unicast" (push to target IP) or "http_mjpeg" (pull server)
    destination_ip: str = "127.0.0.1"
    destination_port: int = Field(default=5000, ge=1024, le=65535)
    host: str = "0.0.0.0"
    port: int = Field(default=8080, ge=1024, le=65535)
    quality: int = Field(default=80, ge=10, le=100)
    stream_fps: int = Field(default=15, ge=1, le=60)


class ExperimentConfig(BaseModel):
    """Protocol validation engine parameters."""

    default_protocol: str = "configs/protocols/bas_e01_a.yaml"
    auto_advance: bool = True
    debounce_threshold: int = Field(default=2, ge=1, le=10)
    allow_skip: bool = True
    require_interaction_confirmation: bool = True


class OrionConfig(BaseModel):
    """Consolidated master application configuration."""

    system: SystemConfig = Field(default_factory=SystemConfig)
    camera: CameraConfig = Field(default_factory=CameraConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    recording: RecordingConfig = Field(default_factory=RecordingConfig)
    streaming: StreamingConfig = Field(default_factory=StreamingConfig)
    experiment: ExperimentConfig = Field(default_factory=ExperimentConfig)

    def save_yaml(self, path: Path) -> None:
        """Serialize configuration to YAML."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(self.model_dump(), f, sort_keys=False, default_flow_style=False)


def load_config(config_path: Path | None = None) -> OrionConfig:
    """Load configuration from config.yaml or return validated defaults."""
    target_path = config_path or (paths.config_dir / "config.yaml")

    if not target_path.is_file():
        # Fallback to configs/base.yaml or return defaults
        legacy_path = paths.configs_legacy_dir / "base.yaml"
        if legacy_path.is_file():
            target_path = legacy_path

    if not target_path.is_file():
        # Return default configuration and write template
        cfg = OrionConfig()
        try:
            cfg.save_yaml(paths.config_dir / "config.yaml")
        except Exception:
            pass
        return cfg

    try:
        with target_path.open("r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}
        return OrionConfig.model_validate(raw_data)
    except Exception as exc:
        raise ConfigurationError(
            f"Failed to parse configuration file '{target_path}': {exc}"
        ) from exc


# Global configuration instance
_active_config: OrionConfig | None = None


def get_config() -> OrionConfig:
    """Get or load active configuration singleton."""
    global _active_config
    if _active_config is None:
        _active_config = load_config()
    return _active_config


def set_config(config: OrionConfig) -> None:
    """Explicitly set configuration singleton."""
    global _active_config
    _active_config = config
