"""Layered Configuration System for ORION BAS AI Copilot.

Enforces configuration priority:
1. Environment variables (highest priority)
2. Command-line overrides
3. YAML environment overrides (e.g. development.yaml, production.yaml)
4. Base YAML configuration (base.yaml)
5. Built-in defaults (lowest priority)

Uses Pydantic Settings (v2) with strict typing.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from orion.core.exceptions import ConfigurationError


class ApiSettings(BaseModel):
    """API & Networking configuration."""

    host: str = Field(default="127.0.0.1", description="Host interface to bind")
    port: int = Field(default=8000, ge=1024, le=65535, description="HTTP port")
    workers: int = Field(default=1, ge=1, le=32, description="Uvicorn worker count")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins",
    )
    secret_key: str = Field(
        default="dev-aerospace-insecure-secret-key-change-in-production",
        min_length=16,
        description="Cryptographic secret key",
    )


class DatabaseSettings(BaseModel):
    """Database & Persistence configuration."""

    url: str = Field(
        default="sqlite+aiosqlite:///./data/orion_dev.db",
        description="SQLAlchemy async connection URL",
    )
    pool_size: int = Field(default=5, ge=1, le=100)
    max_overflow: int = Field(default=10, ge=0, le=50)
    pool_timeout: float = Field(default=30.0, ge=1.0)


class LoggingSettings(BaseModel):
    """Logging and telemetry format configuration."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    format: Literal["json", "console", "pretty"] = Field(default="console")
    file_path: str | None = Field(default="./logs/orion.log")
    rotation_bytes: int = Field(default=52428800)  # 50MB
    backup_count: int = Field(default=10, ge=1)
    metrics_enabled: bool = Field(default=True)
    metrics_port: int = Field(default=9090, ge=1024, le=65535)
    otel_exporter_endpoint: str | None = Field(default=None)


class HardwareSettings(BaseModel):
    """Hardware acceleration profile."""

    accelerator: Literal["cpu", "cuda", "mps", "rocm", "tensorrt", "openvino"] = Field(
        default="cpu"
    )
    device_index: int = Field(default=0, ge=0)
    memory_fraction: float = Field(default=0.75, ge=0.1, le=1.0)
    thermal_limit_celsius: float = Field(default=85.0)


class CameraSettings(BaseModel):
    """Camera capture parameters."""

    source: str = Field(default="0", description="Device index or RTSP URI")
    width: int = Field(default=1920, ge=320)
    height: int = Field(default=1080, ge=240)
    fps: int = Field(default=30, ge=1, le=240)
    buffer_size: int = Field(default=60, ge=5, le=1000)


class RecordingSettings(BaseModel):
    """Experiment recording and storage management."""

    storage_path: str = Field(default="./data/recordings")
    segment_duration_seconds: int = Field(default=600, ge=30)
    min_disk_free_mb: int = Field(default=5120, ge=500)


class AudioSettings(BaseModel):
    """Audio alert annunciation."""

    enabled: bool = Field(default=False)
    volume: float = Field(default=0.8, ge=0.0, le=1.0)
    cooldown_seconds: float = Field(default=10.0, ge=1.0)


def _load_yaml_file(path: Path) -> dict[str, Any]:
    """Safely load a YAML configuration file if it exists."""
    if not path.is_file():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    except Exception as exc:
        raise ConfigurationError(
            f"Failed to parse configuration YAML at {path}: {exc}",
            details={"path": str(path), "error": str(exc)},
        ) from exc


class OrionSettings(BaseSettings):
    """Master layered settings for ORION BAS AI Copilot."""

    # Top-level identification
    env: Literal["development", "testing", "staging", "production"] = Field(
        default="development", alias="ORION_ENV"
    )
    station_id: str = Field(default="BAS-DEV-01", alias="ORION_STATION_ID")
    version: str = Field(default="0.1.0-alpha.0", alias="ORION_VERSION")
    seed: int = Field(default=42, alias="ORION_SEED")

    # Subsystem settings
    api: ApiSettings = Field(default_factory=ApiSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    hardware: HardwareSettings = Field(default_factory=HardwareSettings)
    camera: CameraSettings = Field(default_factory=CameraSettings)
    recording: RecordingSettings = Field(default_factory=RecordingSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)

    model_config = SettingsConfigDict(
        env_prefix="ORION_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def load(cls, config_dir: Path | None = None) -> "OrionSettings":
        """Load layered configuration merging Base YAML, Env YAML, and Environment Variables."""
        if config_dir is None:
            # Look relative to repository root
            config_dir = Path(__file__).resolve().parents[3] / "configs"

        target_env = os.getenv("ORION_ENV", "development").lower()
        base_yaml = _load_yaml_file(config_dir / "base.yaml")
        env_yaml = _load_yaml_file(config_dir / f"{target_env}.yaml")

        # Merge base and env configurations
        merged: dict[str, Any] = {}
        merged.update(base_yaml)
        merged.update(env_yaml)

        # Instantiate settings with env vars overriding YAML
        try:
            return cls(**merged)
        except Exception as exc:
            raise ConfigurationError(
                f"Configuration initialization failed: {exc}",
                details={"env": target_env, "error": str(exc)},
            ) from exc


@lru_cache(maxsize=1)
def get_settings() -> OrionSettings:
    """Singleton cached provider for system settings."""
    return OrionSettings.load()
