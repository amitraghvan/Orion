"""Next-step procedural guidance card widget displaying real-time copilot instructions."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class GuidanceCard(QFrame):
    """Card widget highlighting the current step, expected action, and next step recommendation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("GuidanceCard")
        self.setStyleSheet("""
            #GuidanceCard {
                background-color: #080d1a;
                border: 1px solid #1e3a5f;
                border-left: 4px solid #00e5ff;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(8)

        tag_dot = QLabel("◈")
        tag_dot.setStyleSheet("color: #00e5ff; font-size: 13px; font-weight: bold;")

        title = QLabel("PROCEDURAL GUIDANCE • BAS FLIGHT CO-PILOT")
        title.setStyleSheet(
            "color: #38bdf8; font-family: monospace; font-size: 11px; font-weight: 800; letter-spacing: 1.5px;"
        )

        badge = QLabel("AUTONOMOUS")
        badge.setStyleSheet(
            "background-color: rgba(6, 182, 212, 0.15); color: #00e5ff; "
            "border: 1px solid rgba(0, 229, 255, 0.4); border-radius: 4px; "
            "padding: 2px 8px; font-family: monospace; font-size: 9px; font-weight: 800;"
        )

        header.addWidget(tag_dot)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(badge)
        layout.addLayout(header)

        # Content block
        content_box = QFrame()
        content_box.setStyleSheet(
            "background-color: #040711; border: 1px solid #1e293b; border-radius: 6px;"
        )
        c_layout = QVBoxLayout(content_box)
        c_layout.setContentsMargins(14, 12, 14, 12)
        c_layout.setSpacing(8)

        top_meta_row = QHBoxLayout()
        self._step_badge = QLabel("PHASE: STANDBY")
        self._step_badge.setStyleSheet(
            "background-color: #1e293b; color: #94a3b8; font-family: monospace; "
            "font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 3px;"
        )

        self._action_badge = QLabel("EXPECTED: IDLE")
        self._action_badge.setStyleSheet(
            "background-color: rgba(56, 189, 248, 0.1); color: #38bdf8; font-family: monospace; "
            "font-size: 10px; font-weight: 700; padding: 2px 6px; border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 3px;"
        )

        top_meta_row.addWidget(self._step_badge)
        top_meta_row.addStretch()
        top_meta_row.addWidget(self._action_badge)
        c_layout.addLayout(top_meta_row)

        self._instruction_lbl = QLabel(
            "Select an experiment protocol to initiate mission telemetry guidance."
        )
        self._instruction_lbl.setStyleSheet(
            "color: #f1f5f9; font-size: 13px; font-weight: 600; line-height: 1.4;"
        )
        self._instruction_lbl.setWordWrap(True)
        c_layout.addWidget(self._instruction_lbl)

        # Sub-checklist status
        chk_row = QHBoxLayout()
        chk_row.setSpacing(12)

        self._chk_person = QLabel("● SUBJECT: ACQUIRED")
        self._chk_person.setStyleSheet(
            "color: #10b981; font-family: monospace; font-size: 9px; font-weight: bold;"
        )
        self._chk_fsm = QLabel("● SEQUENCE: SYNCED")
        self._chk_fsm.setStyleSheet(
            "color: #38bdf8; font-family: monospace; font-size: 9px; font-weight: bold;"
        )
        self._chk_audio = QLabel("● AUDIO: ACTIVE")
        self._chk_audio.setStyleSheet(
            "color: #a855f7; font-family: monospace; font-size: 9px; font-weight: bold;"
        )

        chk_row.addWidget(self._chk_person)
        chk_row.addWidget(self._chk_fsm)
        chk_row.addWidget(self._chk_audio)
        chk_row.addStretch()
        c_layout.addLayout(chk_row)

        layout.addWidget(content_box)

    def update_guidance(self, step_num: int, instruction: str, expected_action: str) -> None:
        self._step_badge.setText(f"PHASE {step_num:02d} IN PROGRESS")
        self._step_badge.setStyleSheet(
            "background-color: rgba(16, 185, 129, 0.15); color: #34d399; font-family: monospace; "
            "font-size: 10px; font-weight: 700; padding: 2px 6px; border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 3px;"
        )
        self._instruction_lbl.setText(instruction)
        self._action_badge.setText(f"EXPECTED: {expected_action.upper()}")

    def set_ready(self, experiment_title: str = "", experiment_id: str = "") -> None:
        self._step_badge.setText("PHASE: STANDBY")
        self._step_badge.setStyleSheet(
            "background-color: #1e293b; color: #94a3b8; font-family: monospace; "
            "font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 3px;"
        )
        if experiment_id:
            self._instruction_lbl.setText(
                f"Protocol [{experiment_id}] ready. Click 'INITIATE MISSION' to begin procedural guidance."
            )
            self._action_badge.setText("READY TO START")
        else:
            self._instruction_lbl.setText(
                "Select an experiment protocol to initiate mission telemetry guidance."
            )
            self._action_badge.setText("EXPECTED: IDLE")

    def set_standby(self, instruction: str = "") -> None:
        self._step_badge.setText("PHASE: STANDBY")
        self._step_badge.setStyleSheet(
            "background-color: #1e293b; color: #94a3b8; font-family: monospace; "
            "font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 3px;"
        )
        self._instruction_lbl.setText(
            instruction or "Select an experiment protocol to initiate mission telemetry guidance."
        )
        self._action_badge.setText("EXPECTED: IDLE")

    def set_subsystems(
        self, person_detected: bool, sequence_active: bool, audio_active: bool = True
    ) -> None:
        if person_detected:
            self._chk_person.setText("● SUBJECT: ACQUIRED")
            self._chk_person.setStyleSheet(
                "color: #10b981; font-family: monospace; font-size: 9px; font-weight: bold;"
            )
        else:
            self._chk_person.setText("○ SUBJECT: SEARCHING")
            self._chk_person.setStyleSheet(
                "color: #64748b; font-family: monospace; font-size: 9px; font-weight: bold;"
            )

        if sequence_active:
            self._chk_fsm.setText("● SEQUENCE: ACTIVE")
            self._chk_fsm.setStyleSheet(
                "color: #00e5ff; font-family: monospace; font-size: 9px; font-weight: bold;"
            )
        else:
            self._chk_fsm.setText("● SEQUENCE: SYNCED")
            self._chk_fsm.setStyleSheet(
                "color: #38bdf8; font-family: monospace; font-size: 9px; font-weight: bold;"
            )

        if audio_active:
            self._chk_audio.setText("● AUDIO: ACTIVE")
            self._chk_audio.setStyleSheet(
                "color: #a855f7; font-family: monospace; font-size: 9px; font-weight: bold;"
            )
        else:
            self._chk_audio.setText("○ AUDIO: MUTED")
            self._chk_audio.setStyleSheet(
                "color: #64748b; font-family: monospace; font-size: 9px; font-weight: bold;"
            )
