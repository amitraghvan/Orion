"""Next-step procedural guidance card widget displaying real-time copilot instructions."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class GuidanceCard(QFrame):
    """Card widget highlighting the current step, expected action, and next step recommendation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("GuidanceCard")
        self.setStyleSheet("""
            #GuidanceCard {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f172a, stop:1 #1e1b4b);
                border: 1px solid #38bdf8;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Header row
        header = QHBoxLayout()
        icon_lbl = QLabel("🧭")
        icon_lbl.setStyleSheet("font-size: 16px;")
        title = QLabel("NEXT STEP GUIDANCE (SIH CO-PILOT)")
        title.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
        badge = QLabel("ACTIVE")
        badge.setStyleSheet("background-color: rgba(6, 182, 212, 0.2); color: #22d3ee; border: 1px solid #0891b2; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: 700;")

        header.addWidget(icon_lbl)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(badge)
        layout.addLayout(header)

        # Content block
        content_box = QFrame()
        content_box.setStyleSheet("background-color: #080c14; border: 1px solid #1e293b; border-radius: 6px; padding: 8px;")
        c_layout = QHBoxLayout(content_box)
        c_layout.setContentsMargins(12, 10, 12, 10)
        c_layout.setSpacing(12)

        arrow_lbl = QLabel("➔")
        arrow_lbl.setStyleSheet("color: #06b6d4; font-size: 20px; font-weight: bold;")
        c_layout.addWidget(arrow_lbl)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        self._step_title = QLabel("STEP 01: Awaiting Protocol Start")
        self._step_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 700; text-transform: uppercase;")
        self._instruction_lbl = QLabel("Select an experiment to begin mission guidance.")
        self._instruction_lbl.setStyleSheet("color: #f8fafc; font-size: 13px; font-weight: 700;")
        self._action_lbl = QLabel("Expected Action: idle")
        self._action_lbl.setStyleSheet("color: #22d3ee; font-size: 11px; font-weight: 600;")

        text_layout.addWidget(self._step_title)
        text_layout.addWidget(self._instruction_lbl)
        text_layout.addWidget(self._action_lbl)
        c_layout.addLayout(text_layout)

        layout.addWidget(content_box)

    def update_guidance(self, step_num: int, instruction: str, expected_action: str) -> None:
        self._step_title.setText(f"ACTIVE STEP {step_num:02d}")
        self._instruction_lbl.setText(instruction)
        self._action_lbl.setText(f"Expected Action: {expected_action.upper()}")
