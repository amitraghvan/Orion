"""Station configuration and hardware parameter settings view."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.config import get_config
from app.core.paths import paths


class SettingsView(QWidget):
    """Configures camera parameters, confidence thresholds, audio TTS, and streaming."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()
        self._load_current_values()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Settings Form Card
        frame = QFrame()
        frame.setStyleSheet("background-color: #080c14; border: 1px solid #1e293b; border-radius: 8px; padding: 20px;")
        grid = QGridLayout(frame)
        grid.setSpacing(14)

        row = 0

        # System Mode
        grid.addWidget(self._create_label("OPERATIONAL MODE:"), row, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["offline", "demo"])
        grid.addWidget(self.mode_combo, row, 1)

        # Performance Mode
        row += 1
        grid.addWidget(self._create_label("PERFORMANCE PROFILE:"), row, 0)
        self.perf_combo = QComboBox()
        self.perf_combo.addItems(["balanced", "performance"])
        grid.addWidget(self.perf_combo, row, 1)

        # Camera Source
        row += 1
        grid.addWidget(self._create_label("CAMERA SOURCE / DEVICE:"), row, 0)
        self.source_input = QLineEdit("0")
        grid.addWidget(self.source_input, row, 1)

        # Detection Confidence Threshold
        row += 1
        grid.addWidget(self._create_label("DETECTION CONFIDENCE MIN:"), row, 0)
        self.det_conf = QDoubleSpinBox()
        self.det_conf.setRange(0.05, 0.95)
        self.det_conf.setSingleStep(0.05)
        self.det_conf.setValue(0.25)
        grid.addWidget(self.det_conf, row, 1)

        # HAR Confidence Threshold
        row += 1
        grid.addWidget(self._create_label("HAR CONFIDENCE THRESHOLD:"), row, 0)
        self.har_conf = QDoubleSpinBox()
        self.har_conf.setRange(0.10, 0.95)
        self.har_conf.setSingleStep(0.05)
        self.har_conf.setValue(0.65)
        grid.addWidget(self.har_conf, row, 1)

        # Voice Alerts
        row += 1
        grid.addWidget(self._create_label("OFFLINE VOICE ANNOUNCER:"), row, 0)
        self.voice_chk = QCheckBox("Enable Acoustic Voice Alerts")
        self.voice_chk.setChecked(True)
        grid.addWidget(self.voice_chk, row, 1)

        # C++ Native Engine
        row += 1
        grid.addWidget(self._create_label("C++ NATIVE ENGINE:"), row, 0)
        self.cpp_chk = QCheckBox("Enable C++20 orion_native Core")
        self.cpp_chk.setChecked(True)
        grid.addWidget(self.cpp_chk, row, 1)

        # Local Recording
        row += 1
        grid.addWidget(self._create_label("LOCAL VIDEO RECORDING:"), row, 0)
        self.rec_chk = QCheckBox("Auto-record mission sessions to MP4")
        self.rec_chk.setChecked(True)
        grid.addWidget(self.rec_chk, row, 1)

        layout.addWidget(frame)

        # Save Button
        save_btn = QPushButton("💾 SAVE CONFIGURATION")
        save_btn.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 10px; border-radius: 6px; font-size: 13px;")
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)

        layout.addStretch()

    def _create_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; font-family: monospace;")
        return lbl

    def _load_current_values(self) -> None:
        cfg = get_config()
        self.mode_combo.setCurrentText(cfg.system.mode)
        self.perf_combo.setCurrentText(cfg.system.performance_mode)
        self.source_input.setText(cfg.camera.source)
        self.det_conf.setValue(cfg.models.detection.confidence)
        self.har_conf.setValue(cfg.models.activity.confidence)
        self.voice_chk.setChecked(cfg.audio.voice_enabled)
        self.cpp_chk.setChecked(cfg.system.enable_cpp_engine)
        self.rec_chk.setChecked(cfg.recording.enabled)

    def _save_settings(self) -> None:
        cfg = get_config()
        cfg.system.mode = self.mode_combo.currentText()  # type: ignore[assignment]
        cfg.system.performance_mode = self.perf_combo.currentText()  # type: ignore[assignment]
        cfg.camera.source = self.source_input.text()
        cfg.models.detection.confidence = self.det_conf.value()
        cfg.models.activity.confidence = self.har_conf.value()
        cfg.audio.voice_enabled = self.voice_chk.isChecked()
        cfg.system.enable_cpp_engine = self.cpp_chk.isChecked()
        cfg.recording.enabled = self.rec_chk.isChecked()

        cfg.save_yaml(paths.config_dir / "config.yaml")
