"""Filesystem path manager supporting both development and PyInstaller bundled environments."""

from __future__ import annotations

import sys
from pathlib import Path


class PathManager:
    """Resolves all application paths deterministically without hardcoding."""

    def __init__(self, root_override: Path | None = None) -> None:
        if root_override is not None:
            self._root = root_override.resolve()
        elif getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            # Running in PyInstaller bundle
            self._root = Path(sys._MEIPASS).resolve()  # type: ignore[attr-defined]
        else:
            # Running in normal development environment
            # This file is located at <root>/app/core/paths.py
            self._root = Path(__file__).resolve().parent.parent.parent

    @property
    def root(self) -> Path:
        """Root workspace / application directory."""
        return self._root

    @property
    def app_dir(self) -> Path:
        """Directory for application code."""
        return self._root / "app"

    @property
    def config_dir(self) -> Path:
        """Directory for YAML configuration files."""
        return self._root / "config"

    @property
    def configs_legacy_dir(self) -> Path:
        """Legacy configuration directory."""
        return self._root / "configs"

    @property
    def models_dir(self) -> Path:
        """Base directory for AI weights and manifests."""
        return self._root / "models"

    @property
    def datasets_dir(self) -> Path:
        """Base directory for datasets."""
        return self._root / "datasets"

    @property
    def experiments_dir(self) -> Path:
        """Base directory for experiment protocol definitions."""
        return self._root / "experiments"

    @property
    def recordings_dir(self) -> Path:
        """Output directory for recorded video sessions."""
        d = self._root / "recordings"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def logs_dir(self) -> Path:
        """Output directory for application logs."""
        d = self._root / "logs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def reports_dir(self) -> Path:
        """Output directory for post-mission scientific reports."""
        d = self._root / "reports"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def assets_dir(self) -> Path:
        """Directory for icons, sample media, and test frames."""
        return self._root / "assets"

    @property
    def resources_dir(self) -> Path:
        """Directory for desktop resources (icons, sounds, themes)."""
        d = self._root / "resources"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def database_path(self) -> Path:
        """Path to local SQLite database file."""
        return self._root / "orion.db"

    def resolve_model_path(self, model_filename: str) -> Path:
        """Search for a model weight file across standard model locations."""
        candidates = [
            self.models_dir / model_filename,
            self.models_dir / "weights" / model_filename,
            self.models_dir / "detection" / model_filename,
            self.models_dir / "pose" / model_filename,
            self.models_dir / "activity" / model_filename,
            self.models_dir / "bas_experiment" / model_filename,
            self.models_dir / "engines" / model_filename,
            self.models_dir / "onnx" / model_filename,
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
        # Default to models/weights or direct path
        return (self.models_dir / "weights" / model_filename).resolve()

    def resolve_protocol_path(self, protocol_identifier: str) -> Path:
        """Resolve a protocol definition file by path or identifier."""
        p = Path(protocol_identifier)
        if p.is_file():
            return p.resolve()

        candidates = [
            self.experiments_dir / "definitions" / protocol_identifier,
            self.experiments_dir / "definitions" / f"{protocol_identifier}.yaml",
            self.configs_legacy_dir / "protocols" / protocol_identifier,
            self.configs_legacy_dir / "protocols" / f"{protocol_identifier}.yaml",
            self.config_dir / "protocols" / protocol_identifier,
            self.config_dir / "protocols" / f"{protocol_identifier}.yaml",
            self.datasets_dir / "bas_experiment" / protocol_identifier,
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()

        return (self.configs_legacy_dir / "protocols" / f"{protocol_identifier}.yaml").resolve()


# Global singleton instance
paths = PathManager()
