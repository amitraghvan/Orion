"""Consolidated Mission Control Dashboard view aggregating perception, copilot guidance, and telemetry."""

from __future__ import annotations

from app.core.state_manager import state_manager
from app.experiments.experiment_engine import experiment_engine
from app.ui.widgets.alert_banner import AlertBanner
from app.ui.widgets.guidance_card import GuidanceCard
from app.ui.widgets.status_pill import StatusPill
from app.ui.widgets.timeline_widget import StepTimelineWidget
from app.ui.widgets.video_widget import VideoViewportWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class DashboardView(QWidget):
    """Primary operational command center view."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()
        self._setup_timer()

    def _init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(14)

        # Splitter between left (video/timeline) and right (copilot/status)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #1e293b;
                width: 2px;
            }
        """)

        # ---------------------------------------------------------------------
        # Left Panel (Vision Feed + Timeline + Event Log)
        # ---------------------------------------------------------------------
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Video viewport
        self.video_widget = VideoViewportWidget()
        left_layout.addWidget(self.video_widget, stretch=6)

        # Step progression timeline
        self.timeline_widget = StepTimelineWidget()
        left_layout.addWidget(self.timeline_widget)

        # Telemetry event log table
        log_frame = QFrame()
        log_frame.setStyleSheet(
            "background-color: #050811; border: 1px solid #1e293b; border-radius: 6px;"
        )
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(10, 8, 10, 8)
        log_layout.setSpacing(6)

        log_hdr = QLabel("MISSION TELEMETRY & EVENT AUDIT LOG")
        log_hdr.setStyleSheet(
            "color: #38bdf8; font-family: monospace; font-size: 10px; font-weight: 800; letter-spacing: 1px;"
        )
        log_layout.addWidget(log_hdr)

        self.log_table = QTableWidget(0, 3)
        self.log_table.setHorizontalHeaderLabels(["UTC TIME", "EVENT TYPE", "TELEMETRY DETAILS"])
        self.log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.setStyleSheet("""
            QTableWidget {
                background-color: #030712;
                color: #e2e8f0;
                gridline-color: #111827;
                border: none;
                font-family: monospace;
                font-size: 11px;
                selection-background-color: #1e293b;
            }
            QHeaderView::section {
                background-color: #090e1a;
                color: #94a3b8;
                border: none;
                border-bottom: 1px solid #1e293b;
                padding: 5px 8px;
                font-family: monospace;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }
        """)
        log_layout.addWidget(self.log_table)
        left_layout.addWidget(log_frame, stretch=3)

        splitter.addWidget(left_panel)

        # ---------------------------------------------------------------------
        # Right Panel (Alerts + Guidance + Protocol Status + Evidence)
        # ---------------------------------------------------------------------
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Protocol Violation Alert Banner
        self.alert_banner = AlertBanner()
        right_layout.addWidget(self.alert_banner)

        # Next Step Guidance
        self.guidance_card = GuidanceCard()
        right_layout.addWidget(self.guidance_card)

        # Active Experiment Status Panel
        exp_frame = QFrame()
        exp_frame.setStyleSheet(
            "background-color: #080d1a; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;"
        )
        exp_layout = QVBoxLayout(exp_frame)
        exp_layout.setSpacing(10)

        exp_hdr_layout = QHBoxLayout()
        exp_title_lbl = QLabel("EXPERIMENT MISSION CONTROL")
        exp_title_lbl.setStyleSheet(
            "color: #00e5ff; font-family: monospace; font-size: 11px; font-weight: 800; letter-spacing: 1.5px;"
        )
        self.fsm_pill = StatusPill("FSM", "STANDBY", "gray")
        exp_hdr_layout.addWidget(exp_title_lbl)
        exp_hdr_layout.addStretch()
        exp_hdr_layout.addWidget(self.fsm_pill)
        exp_layout.addLayout(exp_hdr_layout)

        self.exp_name_lbl = QLabel(
            "BAS-EXP-E01-A: E01 Detecting Colour (Variant A: Yellow then Red)"
        )
        self.exp_name_lbl.setStyleSheet("color: #f1f5f9; font-size: 12px; font-weight: 700;")
        self.exp_name_lbl.setWordWrap(True)
        exp_layout.addWidget(self.exp_name_lbl)

        # Progress bar
        prog_meta_row = QHBoxLayout()
        prog_meta_lbl = QLabel("SEQUENCE PROGRESSION")
        prog_meta_lbl.setStyleSheet(
            "color: #64748b; font-family: monospace; font-size: 9px; font-weight: bold;"
        )
        self.pct_lbl = QLabel("0%")
        self.pct_lbl.setStyleSheet(
            "color: #00e5ff; font-family: monospace; font-size: 10px; font-weight: bold;"
        )
        prog_meta_row.addWidget(prog_meta_lbl)
        prog_meta_row.addStretch()
        prog_meta_row.addWidget(self.pct_lbl)
        exp_layout.addLayout(prog_meta_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #1e293b;
                border-radius: 4px;
                background-color: #040711;
                text-align: center;
                color: #ffffff;
                font-family: monospace;
                font-size: 10px;
                font-weight: bold;
                height: 14px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0891b2, stop:1 #00e5ff);
                border-radius: 3px;
            }
        """)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        exp_layout.addWidget(self.progress_bar)

        # Controls row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.start_btn = QPushButton("INITIATE MISSION")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #064e3b;
                color: #34d399;
                border: 1px solid #10b981;
                font-family: monospace;
                font-weight: 800;
                font-size: 11px;
                letter-spacing: 1px;
                padding: 10px 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #047857;
                color: #ffffff;
            }
            QPushButton:disabled {
                background-color: #0b151e;
                color: #334155;
                border: 1px solid #1e293b;
            }
        """)
        self.start_btn.clicked.connect(self._on_start_clicked)

        self.stop_btn = QPushButton("ABORT / HALT")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #450a0a;
                color: #fca5a5;
                border: 1px solid #ef4444;
                font-family: monospace;
                font-weight: 800;
                font-size: 11px;
                letter-spacing: 1px;
                padding: 10px 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #991b1b;
                color: #ffffff;
            }
            QPushButton:disabled {
                background-color: #0b151e;
                color: #334155;
                border: 1px solid #1e293b;
            }
        """)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.stop_btn.setEnabled(False)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        exp_layout.addLayout(btn_layout)

        right_layout.addWidget(exp_frame)

        # Real-time Evidence & Multimodal Panel
        evidence_frame = QFrame()
        evidence_frame.setStyleSheet(
            "background-color: #080d1a; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;"
        )
        ev_layout = QVBoxLayout(evidence_frame)
        ev_layout.setSpacing(8)

        ev_hdr = QLabel("MULTIMODAL EVIDENCE ENGINE")
        ev_hdr.setStyleSheet(
            "color: #c084fc; font-family: monospace; font-size: 11px; font-weight: 800; letter-spacing: 1.5px;"
        )
        ev_layout.addWidget(ev_hdr)

        self.activity_lbl = QLabel("HAR INFERENCE: IDLE [100%]")
        self.activity_lbl.setStyleSheet(
            "color: #f1f5f9; font-family: monospace; font-size: 12px; font-weight: 700;"
        )
        ev_layout.addWidget(self.activity_lbl)

        # Confidence Bar
        self.conf_bar = QProgressBar()
        self.conf_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #1e293b;
                border-radius: 3px;
                background-color: #040711;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 2px;
            }
        """)
        self.conf_bar.setValue(100)
        self.conf_bar.setTextVisible(False)
        ev_layout.addWidget(self.conf_bar)

        # Multi-metric Grid Chips
        chip_grid = QGridLayout()
        chip_grid.setSpacing(6)

        self.entropy_chip = QLabel("ENTROPY: 0.00 [STABLE]")
        self.entropy_chip.setStyleSheet(
            "background-color: #040711; color: #34d399; border: 1px solid #1e293b; "
            "font-family: monospace; font-size: 10px; font-weight: bold; padding: 4px 6px; border-radius: 4px;"
        )

        self.objects_chip = QLabel("OBJECTS: 0")
        self.objects_chip.setStyleSheet(
            "background-color: #040711; color: #38bdf8; border: 1px solid #1e293b; "
            "font-family: monospace; font-size: 10px; font-weight: bold; padding: 4px 6px; border-radius: 4px;"
        )

        self.hands_chip = QLabel("HANDS: 0")
        self.hands_chip.setStyleSheet(
            "background-color: #040711; color: #f59e0b; border: 1px solid #1e293b; "
            "font-family: monospace; font-size: 10px; font-weight: bold; padding: 4px 6px; border-radius: 4px;"
        )

        self.inter_chip = QLabel("HOI: NONE")
        self.inter_chip.setStyleSheet(
            "background-color: #040711; color: #c084fc; border: 1px solid #1e293b; "
            "font-family: monospace; font-size: 10px; font-weight: bold; padding: 4px 6px; border-radius: 4px;"
        )

        chip_grid.addWidget(self.entropy_chip, 0, 0)
        chip_grid.addWidget(self.objects_chip, 0, 1)
        chip_grid.addWidget(self.hands_chip, 1, 0)
        chip_grid.addWidget(self.inter_chip, 1, 1)
        ev_layout.addLayout(chip_grid)

        right_layout.addWidget(evidence_frame)
        right_layout.addStretch()

        splitter.addWidget(right_panel)
        splitter.setSizes([1020, 480])

        main_layout.addWidget(splitter)

    def _setup_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_ui)
        self._timer.start(50)  # 20 Hz UI refresh

    def _refresh_ui(self) -> None:
        # 1. Update Timeline
        spec = experiment_engine.current_spec
        if spec and spec.steps:
            steps_data = [
                {"step_number": s.step_number, "description": s.description} for s in spec.steps
            ]
            self.timeline_widget.set_steps(steps_data, experiment_engine.fsm.current_step_index + 1)
            self.exp_name_lbl.setText(f"{spec.metadata.experiment_id}: {spec.metadata.title}")

            total = len(spec.steps)
            curr = experiment_engine.fsm.current_step_index
            pct = int((curr / total) * 100) if total > 0 else 0
            self.progress_bar.setValue(pct)
            self.pct_lbl.setText(f"{pct}%")

        # 2. Update FSM State
        fsm_state = experiment_engine.fsm.state.value
        fsm_color = (
            "green"
            if fsm_state in ("RUNNING", "STEP_IN_PROGRESS")
            else ("cyan" if fsm_state == "COMPLETED" else "gray")
        )
        self.fsm_pill.set_status(fsm_state, fsm_color)

        self.start_btn.setEnabled(fsm_state in ("LOADED", "IDLE", "COMPLETED", "ABORTED"))
        self.stop_btn.setEnabled(fsm_state in ("RUNNING", "STEP_IN_PROGRESS", "PAUSED"))

        # 3. Update Evidence
        snapshot = state_manager.latest_perception
        conf_pct = int(snapshot.activity_confidence * 100)
        act_text = f"HAR INFERENCE: {snapshot.recognized_activity.upper()} [{conf_pct}%]"
        self.activity_lbl.setText(act_text)
        self.conf_bar.setValue(conf_pct)

        # Bar color based on confidence
        if conf_pct >= 70:
            bar_color = "#10b981"
        elif conf_pct >= 40:
            bar_color = "#f59e0b"
        else:
            bar_color = "#ef4444"
        self.conf_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #1e293b;
                border-radius: 3px;
                background-color: #040711;
                height: 8px;
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 2px;
            }}
        """)

        entropy_val = snapshot.activity_entropy
        status_text = (
            "STABLE"
            if entropy_val < 0.8
            else ("EVALUATING" if entropy_val < 1.5 else "HIGH_VARIANCE")
        )
        self.entropy_chip.setText(f"ENTROPY: {entropy_val:.2f} [{status_text}]")
        self.objects_chip.setText(f"OBJECTS: {len(snapshot.detected_objects)}")
        self.hands_chip.setText(f"HANDS: {len(snapshot.hands)}")
        inter_txt = (
            f"HOI: {len(snapshot.interactions)} ACTIVE" if snapshot.interactions else "HOI: NOMINAL"
        )
        self.inter_chip.setText(inter_txt)

        # 4. Update Logs Table
        timeline = experiment_engine.get_timeline()
        if len(timeline) != self.log_table.rowCount():
            self.log_table.setRowCount(len(timeline))
            for row_idx, item in enumerate(reversed(timeline)):
                self.log_table.setItem(row_idx, 0, QTableWidgetItem(item.get("timestamp", "")))
                self.log_table.setItem(row_idx, 1, QTableWidgetItem(item.get("type", "")))
                self.log_table.setItem(row_idx, 2, QTableWidgetItem(item.get("details", "")))

    def _on_start_clicked(self) -> None:
        try:
            experiment_engine.start_experiment()
        except Exception as exc:
            self.alert_banner.show_alert(str(exc), severity="CRITICAL")

    def _on_stop_clicked(self) -> None:
        experiment_engine.stop_experiment()
