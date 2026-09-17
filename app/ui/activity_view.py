"""Human Activity Recognition (HAR) probability distribution and temporal window inspection."""

from __future__ import annotations

from app.core.state_manager import state_manager
from app.intelligence.temporal_engine import BAS_HAR_CLASSES_8
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class ActivityView(QWidget):
    """Visualizes ST-GCN multi-class activity probability distribution and temporal telemetry."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._bars: dict[str, QProgressBar] = {}
        self._labels: dict[str, QLabel] = {}
        self._init_ui()
        self._setup_timer()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Header summary
        hdr_frame = QFrame()
        hdr_frame.setStyleSheet(
            "background-color: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 12px;"
        )
        h_layout = QHBoxLayout(hdr_frame)

        self.current_act_lbl = QLabel("CURRENT ACTIVITY: IDLE (100%)")
        self.current_act_lbl.setStyleSheet("color: #38bdf8; font-size: 15px; font-weight: 800;")
        self.uncertainty_lbl = QLabel("STATUS: NOMINAL | SHANNON ENTROPY: 0.00")
        self.uncertainty_lbl.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold;")

        h_layout.addWidget(self.current_act_lbl)
        h_layout.addStretch()
        h_layout.addWidget(self.uncertainty_lbl)
        layout.addWidget(hdr_frame)

        # Multi-class probability bars grid
        grid_frame = QFrame()
        grid_frame.setStyleSheet(
            "background-color: #080c14; border: 1px solid #1e293b; border-radius: 8px; padding: 16px;"
        )
        g_layout = QGridLayout(grid_frame)
        g_layout.setSpacing(12)

        for idx, act in enumerate(BAS_HAR_CLASSES_8):
            lbl = QLabel(f"{act.upper()}:")
            lbl.setStyleSheet(
                "color: #94a3b8; font-size: 11px; font-weight: bold; font-family: monospace;"
            )
            lbl.setFixedWidth(160)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(100 if act == "idle" else 0)
            bar.setTextVisible(True)
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

            val_lbl = QLabel("0.0%")
            val_lbl.setStyleSheet(
                "color: #38bdf8; font-size: 11px; font-weight: bold; font-family: monospace;"
            )
            val_lbl.setFixedWidth(50)

            self._bars[act] = bar
            self._labels[act] = val_lbl

            g_layout.addWidget(lbl, idx, 0)
            g_layout.addWidget(bar, idx, 1)
            g_layout.addWidget(val_lbl, idx, 2)

        layout.addWidget(grid_frame, stretch=1)

    def _setup_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(50)

    def _refresh(self) -> None:
        snapshot = state_manager.latest_perception
        top_act = snapshot.recognized_activity
        conf = snapshot.activity_confidence
        ent = snapshot.activity_entropy
        status = snapshot.uncertainty_status

        self.current_act_lbl.setText(f"CURRENT ACTIVITY: {top_act.upper()} ({conf * 100:.1f}%)")
        status_color = "#ef4444" if status == "UNCERTAIN" else "#10b981"
        self.uncertainty_lbl.setText(f"STATUS: {status} | SHANNON ENTROPY: {ent:.2f}")
        self.uncertainty_lbl.setStyleSheet(
            f"color: {status_color}; font-size: 12px; font-weight: bold;"
        )

        # Update bars (simulate nominal distribution if equal)
        for act in BAS_HAR_CLASSES_8:
            if act == top_act:
                p_val = int(conf * 100)
            else:
                p_val = int((1.0 - conf) * 100 / (len(BAS_HAR_CLASSES_8) - 1))
            self._bars[act].setValue(p_val)
            self._labels[act].setText(f"{p_val}%")
