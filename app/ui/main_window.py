"""Master Mission Control MainWindow assembling all operational cockpit modules."""

from __future__ import annotations

from datetime import UTC, datetime

from app.camera.camera_manager import camera_manager
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
from PySide6.QtCore import QTimer
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


class MainWindow(QMainWindow):
    """Aerospace-grade Mission Control desktop window for Bharatiya Antariksh Station."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ORION — Offline AI BAS Experiment Assistant • SIH26174")
        self.resize(1620, 980)
        self.setMinimumSize(1280, 720)

        self._setup_stylesheet()
        self._init_ui()
        self._setup_clock_timer()

    def _setup_stylesheet(self) -> None:
        self.setStyleSheet("""
            QMainWindow {
                background-color: #030712;
            }
            QWidget {
                color: #e2e8f0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            }
            QPushButton {
                border: none;
                text-align: left;
                padding: 10px 16px;
                font-family: monospace;
                font-size: 11px;
                font-weight: 700;
                color: #64748b;
                border-radius: 4px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: #0b1329;
                color: #38bdf8;
            }
            QPushButton:checked {
                background-color: #082f49;
                color: #00e5ff;
                font-weight: 800;
                border-left: 3px solid #00e5ff;
            }
            QScrollBar:vertical {
                border: none;
                background: #030712;
                width: 6px;
            }
            QScrollBar::handle:vertical {
                background: #1e293b;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #0284c7;
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
        top_bar.setStyleSheet(
            "background-color: #030712; border-bottom: 1px solid #111827; min-height: 48px;"
        )
        t_layout = QHBoxLayout(top_bar)
        t_layout.setContentsMargins(18, 6, 18, 6)
        t_layout.setSpacing(14)

        # Brand
        brand_col = QVBoxLayout()
        brand_col.setSpacing(1)

        brand_lbl = QLabel("ORION")
        brand_lbl.setStyleSheet(
            "color: #00e5ff; font-family: monospace; font-size: 16px; font-weight: 900; letter-spacing: 3px;"
        )
        sub_lbl = QLabel("BHARATIYA ANTARIKSH STATION • AI COPILOT")
        sub_lbl.setStyleSheet(
            "color: #475569; font-family: monospace; font-size: 8px; font-weight: 800; letter-spacing: 1.5px;"
        )
        brand_col.addWidget(brand_lbl)
        brand_col.addWidget(sub_lbl)
        t_layout.addLayout(brand_col)

        t_layout.addSpacing(20)

        # Telemetry Status Pills
        self.pill_system = StatusPill("SYS", "READY", "green")
        self.pill_camera = StatusPill("CAM01", "STREAMING", "green")
        self.pill_ai = StatusPill("AI", "ACTIVE", "green")
        self.pill_gpu = StatusPill("COMPUTE", "MPS ACCEL", "cyan")
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
        self.clock_lbl = QLabel("2026-09-17 00:00:00 UTC")
        self.clock_lbl.setStyleSheet(
            "color: #00e5ff; font-family: monospace; font-size: 12px; font-weight: bold; "
            "background-color: #050b14; border: 1px solid #111827; padding: 4px 10px; border-radius: 4px;"
        )
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
        sidebar.setStyleSheet("background-color: #030712; border-right: 1px solid #111827;")
        s_layout = QVBoxLayout(sidebar)
        s_layout.setContentsMargins(10, 14, 10, 14)
        s_layout.setSpacing(3)

        nav_title = QLabel("MISSION COCKPIT MODULES")
        nav_title.setStyleSheet(
            "color: #334155; font-family: monospace; font-size: 9px; font-weight: 800; "
            "padding: 6px 10px; letter-spacing: 1.5px;"
        )
        s_layout.addWidget(nav_title)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        # High-tech geometric tactical glyphs (ZERO casual emojis)
        nav_items = [
            ("◈  DASHBOARD", 0),
            ("⦿  LIVE VISION", 1),
            ("▲  EXPERIMENT", 2),
            ("⬡  ACTIVITY (HAR)", 3),
            ("■  RECORDINGS", 4),
            ("≡  MISSION REPORTS", 5),
            ("◆  AI MODELS", 6),
            ("▣  DATASETS", 7),
            ("⊕  DIAGNOSTICS", 8),
            ("⊞  SETTINGS", 9),
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
        badge.setStyleSheet(
            "background-color: #050b14; border: 1px solid #111827; border-radius: 6px; padding: 10px;"
        )
        bg_layout = QVBoxLayout(badge)
        bg_layout.setContentsMargins(8, 6, 8, 6)
        bg_layout.setSpacing(2)
        bg_lbl1 = QLabel("● 100% AIR-GAPPED")
        bg_lbl1.setStyleSheet(
            "color: #10b981; font-family: monospace; font-size: 10px; font-weight: 900;"
        )
        bg_lbl2 = QLabel("ZERO INTERNET TELEMETRY")
        bg_lbl2.setStyleSheet(
            "color: #475569; font-family: monospace; font-size: 8px; font-weight: bold;"
        )
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

        self.stack.addWidget(self.dashboard_view)  # 0
        self.stack.addWidget(self.live_view)  # 1
        self.stack.addWidget(self.experiment_view)  # 2
        self.stack.addWidget(self.activity_view)  # 3
        self.stack.addWidget(self.recordings_view)  # 4
        self.stack.addWidget(self.reports_view)  # 5
        self.stack.addWidget(self.model_view)  # 6
        self.stack.addWidget(self.dataset_view)  # 7
        self.stack.addWidget(self.diagnostics_view)  # 8
        self.stack.addWidget(self.settings_view)  # 9

        b_layout.addWidget(self.stack, stretch=1)
        root_layout.addWidget(body, stretch=1)

        # ---------------------------------------------------------------------
        # 3. Bottom Status Footer
        # ---------------------------------------------------------------------
        footer = QFrame()
        footer.setStyleSheet(
            "background-color: #030712; border-top: 1px solid #111827; min-height: 28px;"
        )
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(18, 4, 18, 4)
        f_layout.setSpacing(18)

        self.footer_station_lbl = QLabel(
            "BHARATIYA ANTARIKSH STATION • MICROGRAVITY EXPERIMENT DECK 01"
        )
        self.footer_station_lbl.setStyleSheet(
            "color: #475569; font-family: monospace; font-size: 9px; font-weight: bold;"
        )
        f_layout.addWidget(self.footer_station_lbl)

        f_layout.addStretch()

        self.footer_fps_lbl = QLabel("FPS: 30.0")
        self.footer_fps_lbl.setStyleSheet(
            "color: #00e5ff; font-family: monospace; font-size: 10px; font-weight: bold;"
        )
        self.footer_lat_lbl = QLabel("LAT: 32.0 ms")
        self.footer_lat_lbl.setStyleSheet(
            "color: #c084fc; font-family: monospace; font-size: 10px; font-weight: bold;"
        )
        self.footer_eng_lbl = QLabel("C++ NATIVE ENGINE: ENGAGED")
        self.footer_eng_lbl.setStyleSheet(
            "color: #10b981; font-family: monospace; font-size: 10px; font-weight: bold;"
        )

        self.footer_sih_lbl = QLabel("SIH26174 COMPLIANT")
        self.footer_sih_lbl.setStyleSheet(
            "color: #38bdf8; font-family: monospace; font-size: 9px; font-weight: 800;"
        )

        f_layout.addWidget(self.footer_fps_lbl)
        f_layout.addWidget(self.footer_lat_lbl)
        f_layout.addWidget(self.footer_eng_lbl)
        f_layout.addWidget(self.footer_sih_lbl)

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

        # Camera status check
        cam_active = camera_manager.is_active or tel.camera_connected
        cam_color = "green" if cam_active else "red"
        cam_stat = "STREAMING" if cam_active else "OFFLINE"
        self.pill_camera.set_status(cam_stat, cam_color)

        rec_stat = "RECORDING" if state_manager._is_recording else "STANDBY"
        rec_color = "red" if state_manager._is_recording else "gray"
        self.pill_rec.set_status(rec_stat, rec_color)
