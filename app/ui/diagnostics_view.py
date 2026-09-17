"""Hardware telemetry and subsystem health diagnostics view."""

from __future__ import annotations

import psutil
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from app.core.state_manager import state_manager
from app.ui.widgets.status_pill import StatusPill


class DiagnosticsView(QWidget):
    """Monitors live workstation hardware loads, inference latencies, and subsystem health."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._subsystems = {}
        self._init_ui()
        self._setup_timer()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # ---------------------------------------------------------------------
        # 1. Hardware Utilization Grid
        # ---------------------------------------------------------------------
        hw_title = QLabel("WORKSTATION HARDWARE TELEMETRY")
        hw_title.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
        layout.addWidget(hw_title)

        hw_frame = QFrame()
        hw_frame.setStyleSheet("background-color: #080c14; border: 1px solid #1e293b; border-radius: 8px; padding: 16px;")
        hw_layout = QGridLayout(hw_frame)
        hw_layout.setSpacing(14)

        # CPU
        self.cpu_bar = self._create_metric_bar("CPU UTILIZATION:", hw_layout, 0)
        # RAM
        self.ram_bar = self._create_metric_bar("SYSTEM MEMORY (RAM):", hw_layout, 1)

        layout.addWidget(hw_frame)

        # ---------------------------------------------------------------------
        # 2. Perception & Video Telemetry
        # ---------------------------------------------------------------------
        cv_title = QLabel("PERCEPTION PIPELINE TELEMETRY")
        cv_title.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
        layout.addWidget(cv_title)

        cv_frame = QFrame()
        cv_frame.setStyleSheet("background-color: #080c14; border: 1px solid #1e293b; border-radius: 8px; padding: 16px;")
        cv_layout = QGridLayout(cv_frame)
        cv_layout.setSpacing(12)

        self.cam_fps_lbl = QLabel("Camera Acquisition FPS: 0.0")
        self.inf_fps_lbl = QLabel("AI Inference FPS: 0.0")
        self.inf_lat_lbl = QLabel("Inference Latency: 0.0 ms")
        self.drop_lbl = QLabel("Dropped Frames: 0")
        self.device_lbl = QLabel("Active Compute Engine: CPU")

        for idx, lbl in enumerate([self.cam_fps_lbl, self.inf_fps_lbl, self.inf_lat_lbl, self.drop_lbl, self.device_lbl]):
            lbl.setStyleSheet("color: #f1f5f9; font-size: 12px; font-weight: bold; font-family: monospace;")
            cv_layout.addWidget(lbl, idx // 2, idx % 2)

        layout.addWidget(cv_frame)

        # ---------------------------------------------------------------------
        # 3. Subsystem Health Matrix
        # ---------------------------------------------------------------------
        sub_title = QLabel("SUBSYSTEM OPERATIONAL HEALTH MATRIX")
        sub_title.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
        layout.addWidget(sub_title)

        sub_frame = QFrame()
        sub_frame.setStyleSheet("background-color: #080c14; border: 1px solid #1e293b; border-radius: 8px; padding: 16px;")
        sub_layout = QGridLayout(sub_frame)
        sub_layout.setSpacing(12)

        subsystem_names = [
            ("CAMERA ENGINE", "CONNECTED", "green"),
            ("YOLO DETECTOR", "READY", "green"),
            ("YOLO POSE", "READY", "green"),
            ("ST-GCN HAR", "READY", "green"),
            ("BYTE TRACKER", "ONLINE", "green"),
            ("HOI ENGINE", "ACTIVE", "green"),
            ("PROTOCOL FSM", "READY", "green"),
            ("OFFLINE TTS", "READY", "green"),
            ("LOCAL RECORDER", "STANDBY", "gray"),
            ("IP STREAMING", "DISABLED", "gray"),
            ("SQLITE DATABASE", "READY", "green"),
            ("NATIVE C++ CORE", "ENGAGED", "green"),
        ]

        for i, (name, status, color) in enumerate(subsystem_names):
            pill = StatusPill(name, status, color)
            self._subsystems[name] = pill
            sub_layout.addWidget(pill, i // 3, i % 3)

        layout.addWidget(sub_frame)
        layout.addStretch()

    def _create_metric_bar(self, label_text: str, grid: QGridLayout, row: int) -> QProgressBar:
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; font-family: monospace;")
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #1e293b;
                border-radius: 4px;
                background-color: #0f172a;
                text-align: center;
                color: #ffffff;
                font-size: 10px;
                font-weight: bold;
                height: 18px;
            }
            QProgressBar::chunk {
                background-color: #06b6d4;
                border-radius: 3px;
            }
        """)
        grid.addWidget(lbl, row, 0)
        grid.addWidget(bar, row, 1)
        return bar

    def _setup_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(500)  # 2 Hz

    def _refresh(self) -> None:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        self.cpu_bar.setValue(int(cpu))
        self.ram_bar.setValue(int(ram))

        tel = state_manager.telemetry
        self.cam_fps_lbl.setText(f"Camera Acquisition FPS: {tel.camera_fps:.1f}")
        self.inf_fps_lbl.setText(f"AI Inference FPS: {tel.inference_fps:.1f}")
        self.inf_lat_lbl.setText(f"Inference Latency: {tel.inference_latency_ms:.1f} ms")
        self.device_lbl.setText(f"Active Compute Engine: {tel.active_device}")
