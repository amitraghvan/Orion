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
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

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
        left_layout.setSpacing(12)

        # Video viewport
        self.video_widget = VideoViewportWidget()
        left_layout.addWidget(self.video_widget, stretch=5)

        # Step progression timeline
        self.timeline_widget = StepTimelineWidget()
        left_layout.addWidget(self.timeline_widget)

        # Telemetry event log table
        log_frame = QFrame()
        log_frame.setStyleSheet(
            "background-color: #0f172a; border: 1px solid #1e293b; border-radius: 6px;"
        )
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(10, 8, 10, 8)
        log_layout.setSpacing(6)

        log_hdr = QLabel("MISSION TELEMETRY & EVENT LOG")
        log_hdr.setStyleSheet(
            "color: #94a3b8; font-size: 10px; font-weight: 800; letter-spacing: 1px;"
        )
        log_layout.addWidget(log_hdr)

        self.log_table = QTableWidget(0, 3)
        self.log_table.setHorizontalHeaderLabels(["TIME", "EVENT", "DETAILS"])
        self.log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.log_table.setStyleSheet("""
            QTableWidget {
                background-color: #080c14;
                color: #e2e8f0;
                gridline-color: #1e293b;
                border: none;
                font-family: monospace;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #94a3b8;
                border: 1px solid #1e293b;
                padding: 4px;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        log_layout.addWidget(self.log_table)
        left_layout.addWidget(log_frame, stretch=2)

        splitter.addWidget(left_panel)

        # ---------------------------------------------------------------------
        # Right Panel (Alerts + Guidance + Protocol Status + Evidence)
        # ---------------------------------------------------------------------
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Protocol Violation Alert Banner
        self.alert_banner = AlertBanner()
        right_layout.addWidget(self.alert_banner)

        # Next Step Guidance
        self.guidance_card = GuidanceCard()
        right_layout.addWidget(self.guidance_card)

        # Active Experiment Status Panel
        exp_frame = QFrame()
        exp_frame.setStyleSheet(
            "background-color: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;"
        )
        exp_layout = QVBoxLayout(exp_frame)
        exp_layout.setSpacing(8)

        exp_hdr_layout = QHBoxLayout()
        exp_title_lbl = QLabel("EXPERIMENT STATUS & CONTROLS")
        exp_title_lbl.setStyleSheet(
            "color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1px;"
        )
        self.fsm_pill = StatusPill("FSM", "IDLE", "gray")
        exp_hdr_layout.addWidget(exp_title_lbl)
        exp_hdr_layout.addStretch()
        exp_hdr_layout.addWidget(self.fsm_pill)
        exp_layout.addLayout(exp_hdr_layout)

        self.exp_name_lbl = QLabel("No experiment protocol loaded")
        self.exp_name_lbl.setStyleSheet("color: #f8fafc; font-size: 13px; font-weight: bold;")
        exp_layout.addWidget(self.exp_name_lbl)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #334155;
                border-radius: 4px;
                background-color: #080c14;
                text-align: center;
                color: #ffffff;
                font-size: 10px;
                font-weight: bold;
                height: 16px;
            }
            QProgressBar::chunk {
                background-color: #06b6d4;
                border-radius: 3px;
            }
        """)
        self.progress_bar.setValue(0)
        exp_layout.addWidget(self.progress_bar)

        # Controls row
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶ START MISSION")
        self.start_btn.setStyleSheet(
            "background-color: #059669; color: white; font-weight: bold; padding: 8px; border-radius: 4px;"
        )
        self.start_btn.clicked.connect(self._on_start_clicked)

        self.stop_btn = QPushButton("⏹ HALT")
        self.stop_btn.setStyleSheet(
            "background-color: #dc2626; color: white; font-weight: bold; padding: 8px; border-radius: 4px;"
        )
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.stop_btn.setEnabled(False)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        exp_layout.addLayout(btn_layout)

        right_layout.addWidget(exp_frame)

        # Real-time Evidence & Multimodal Panel
        evidence_frame = QFrame()
        evidence_frame.setStyleSheet(
            "background-color: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;"
        )
        ev_layout = QVBoxLayout(evidence_frame)
        ev_layout.setSpacing(6)

        ev_hdr = QLabel("MULTIMODAL EVIDENCE ENGINE")
        ev_hdr.setStyleSheet(
            "color: #a855f7; font-size: 11px; font-weight: 800; letter-spacing: 1px;"
        )
        ev_layout.addWidget(ev_hdr)

        self.activity_lbl = QLabel("Recognized Activity: IDLE (100%)")
        self.activity_lbl.setStyleSheet("color: #e2e8f0; font-size: 12px; font-weight: bold;")
        self.entropy_lbl = QLabel("Shannon Entropy: 0.00 | Status: NOMINAL")
        self.entropy_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.objects_lbl = QLabel("Tracked Objects: 0 | Hands: 0 | Interactions: 0")
        self.objects_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")

        ev_layout.addWidget(self.activity_lbl)
        ev_layout.addWidget(self.entropy_lbl)
        ev_layout.addWidget(self.objects_lbl)

        right_layout.addWidget(evidence_frame)
        right_layout.addStretch()

        splitter.addWidget(right_panel)
        splitter.setSizes([1000, 500])

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
        act_text = f"Activity: {snapshot.recognized_activity.upper()} ({snapshot.activity_confidence * 100:.0f}%)"
        self.activity_lbl.setText(act_text)
        self.entropy_lbl.setText(
            f"Entropy: {snapshot.activity_entropy:.2f} | Status: {snapshot.uncertainty_status}"
        )
        self.objects_lbl.setText(
            f"Tracked Objects: {len(snapshot.detected_objects)} | Hands: {len(snapshot.hands)} | Interactions: {len(snapshot.interactions)}"
        )

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
