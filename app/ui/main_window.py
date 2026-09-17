"""Master Mission Control MainWindow assembling all operational cockpit modules."""

from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.paths import paths
from app.core.state_manager import state_manager
from app.ui.activity_view import ActivityView
from app.ui.dashboard import DashboardView
from app.ui.dataset_view import DatasetView
from app.ui.diagnostics_view import DiagnosticsView
from app.ui.experiment_view import ExperimentView
from app.ui.live_view import LiveVisionView
from app.ui.model_view import ModelManagerView
from app.ui.recordings_view import RecordingsView
from app.ui.reports_view import ReportsView
from app.ui.settings_view import SettingsView
from app.ui.widgets.status_pill import StatusPill


class MainWindow(QMainWindow):
    """Aerospace-grade Mission Control desktop window for Bharatiya Antariksh Station."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ORION — Offline AI BAS Experiment Assistant • SIH26174")
        self.resize(1600, 960)
        self.setMinimumSize(1280, 720)

        self._setup_stylesheet()
        self._init_ui()
        self._setup_clock_timer()

    def _setup_stylesheet(self) -> None:
        self.setStyleSheet("""
            QMainWindow {
                background-color: #050811;
            }
            QWidget {
                color: #e2e8f0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }
            QPushButton {
                border: none;
                text-align: left;
                padding: 10px 16px;
                font-size: 12px;
                font-weight: 600;
                color: #94a3b8;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #1e293b;
                color: #38bdf8;
            }
            QPushButton:checked {
                background-color: #0c4a6e;
                color: #38bdf8;
                font-weight: bold;
                border-left: 3px solid #06b6d4;
            }
        """)

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ---------------------------------------------------------------------
        # 1. Top Station Cockpit Header Bar
        # ---------------------------------------------------------------------
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #080c14; border-bottom: 1px solid #1e293b; min-height: 48px;")
        t_layout = QHBoxLayout(top_bar)
        t_layout.setContentsMargins(16, 6, 16, 6)
        t_layout.setSpacing(12)

        # Brand
        brand_lbl = QLabel("ORION")
        brand_lbl.setStyleSheet("color: #38bdf8; font-size: 16px; font-weight: 900; letter-spacing: 2px;")
        sub_lbl = QLabel("BAS AI COPILOT")
        sub_lbl.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 700; letter-spacing: 1px;")

        t_layout.addWidget(brand_lbl)
        t_layout.addWidget(sub_lbl)
        t_layout.addSpacing(16)

        # Telemetry Status Pills
        self.pill_system = StatusPill("SYSTEM", "READY", "green")
        self.pill_camera = StatusPill("CAM01", "CONNECTED", "green")
        self.pill_ai = StatusPill("AI", "ACTIVE", "green")
        self.pill_gpu = StatusPill("COMPUTE", "AUTO", "cyan")
        self.pill_rec = StatusPill("REC", "STANDBY", "gray")
        self.pill_stream = StatusPill("STREAM", "OFF", "gray")

        t_layout.addWidget(self.pill_system)
        t_layout.addWidget(self.pill_camera)
        t_layout.addWidget(self.pill_ai)
        t_layout.addWidget(self.pill_gpu)
        t_layout.addWidget(self.pill_rec)
        t_layout.addWidget(self.pill_stream)

        t_layout.addStretch()

        # UTC Station Clock
        self.clock_lbl = QLabel("2026-09-16 00:00:00 UTC")
        self.clock_lbl.setStyleSheet("color: #94a3b8; font-family: monospace; font-size: 12px; font-weight: bold;")
        t_layout.addWidget(self.clock_lbl)

        root_layout.addWidget(top_bar)

        # ---------------------------------------------------------------------
        # 2. Main Body (Sidebar Navigation + Stacked View Pages)
        # ---------------------------------------------------------------------
        body = QWidget()
        b_layout = QHBoxLayout(body)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("background-color: #080c14; border-right: 1px solid #1e293b;")
        s_layout = QVBoxLayout(sidebar)
        s_layout.setContentsMargins(8, 12, 8, 12)
        s_layout.setSpacing(4)

        nav_title = QLabel("MISSION MODULES")
        nav_title.setStyleSheet("color: #475569; font-size: 10px; font-weight: 800; padding: 6px 12px; letter-spacing: 1px;")
        s_layout.addWidget(nav_title)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        nav_items = [
            ("⬚  Dashboard", 0),
            ("◉  Live Vision", 1),
            ("📋  Experiment", 2),
            ("📊  Activity (HAR)", 3),
            ("📹  Recordings", 4),
            ("📑  Mission Reports", 5),
            ("🧠  AI Models", 6),
            ("📦  Datasets", 7),
            ("🩺  Diagnostics", 8),
            ("⚙️  Settings", 9),
        ]

        self.nav_buttons = []
        for text, page_idx in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            if page_idx == 0:
                btn.setChecked(True)
            self.btn_group.addButton(btn, page_idx)
            btn.clicked.connect(lambda _, idx=page_idx: self._switch_page(idx))
            s_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        s_layout.addStretch()

        # Air-gapped badge
        badge = QFrame()
        badge.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 8px;")
        bg_layout = QVBoxLayout(badge)
        bg_layout.setContentsMargins(8, 6, 8, 6)
        bg_lbl1 = QLabel("100% OFFLINE")
        bg_lbl1.setStyleSheet("color: #10b981; font-size: 10px; font-weight: 900;")
        bg_lbl2 = QLabel("AIR-GAPPED STATION")
        bg_lbl2.setStyleSheet("color: #64748b; font-size: 9px; font-weight: bold;")
        bg_layout.addWidget(bg_lbl1)
        bg_layout.addWidget(bg_lbl2)
        s_layout.addWidget(badge)

        b_layout.addWidget(sidebar)

        # Central Stacked Widget
        self.stack = QStackedWidget()
        self.dashboard_view = DashboardView()
        self.live_view = LiveVisionView()
        self.experiment_view = ExperimentView()
        self.activity_view = ActivityView()
        self.recordings_view = RecordingsView()
        self.reports_view = ReportsView()
        self.model_view = ModelManagerView()
        self.dataset_view = DatasetView()
        self.diagnostics_view = DiagnosticsView()
        self.settings_view = SettingsView()

        self.stack.addWidget(self.dashboard_view)   # 0
        self.stack.addWidget(self.live_view)        # 1
        self.stack.addWidget(self.experiment_view)  # 2
        self.stack.addWidget(self.activity_view)    # 3
        self.stack.addWidget(self.recordings_view)  # 4
        self.stack.addWidget(self.reports_view)     # 5
        self.stack.addWidget(self.model_view)       # 6
        self.stack.addWidget(self.dataset_view)     # 7
        self.stack.addWidget(self.diagnostics_view) # 8
        self.stack.addWidget(self.settings_view)    # 9

        b_layout.addWidget(self.stack, stretch=1)
        root_layout.addWidget(body, stretch=1)

        # ---------------------------------------------------------------------
        # 3. Bottom Status Footer
        # ---------------------------------------------------------------------
        footer = QFrame()
        footer.setStyleSheet("background-color: #080c14; border-top: 1px solid #1e293b; min-height: 28px;")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(16, 4, 16, 4)
        f_layout.setSpacing(16)

        self.footer_station_lbl = QLabel("BHARATIYA ANTARIKSH STATION • SCIENCE MODULE 01")
        self.footer_station_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        f_layout.addWidget(self.footer_station_lbl)

        f_layout.addStretch()

        self.footer_fps_lbl = QLabel("FPS: 0.0")
        self.footer_fps_lbl.setStyleSheet("color: #38bdf8; font-family: monospace; font-size: 10px; font-weight: bold;")
        self.footer_lat_lbl = QLabel("LAT: 0.0 ms")
        self.footer_lat_lbl.setStyleSheet("color: #a855f7; font-family: monospace; font-size: 10px; font-weight: bold;")
        self.footer_eng_lbl = QLabel("C++ ENGINE: ENGAGED")
        self.footer_eng_lbl.setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold;")

        f_layout.addWidget(self.footer_fps_lbl)
        f_layout.addWidget(self.footer_lat_lbl)
        f_layout.addWidget(self.footer_eng_lbl)

        root_layout.addWidget(footer)

    def _switch_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    def _setup_clock_timer(self) -> None:
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick)
        self._clock_timer.start(1000)

    def _tick(self) -> None:
        now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        self.clock_lbl.setText(now_str)

        # Telemetry updates
        tel = state_manager.telemetry
        self.footer_fps_lbl.setText(f"FPS: {tel.camera_fps:.1f}")
        self.footer_lat_lbl.setText(f"LAT: {tel.inference_latency_ms:.1f} ms")
        self.pill_gpu.set_status(tel.active_device, "cyan")

        cam_color = "green" if tel.camera_connected else "red"
        cam_stat = "CONNECTED" if tel.camera_connected else "OFFLINE"
        self.pill_camera.set_status(cam_stat, cam_color)

        rec_stat = "ACTIVE" if state_manager._is_recording else "STANDBY"
        rec_color = "red" if state_manager._is_recording else "gray"
        self.pill_rec.set_status(rec_stat, rec_color)
