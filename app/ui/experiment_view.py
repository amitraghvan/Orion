"""Experiment protocol specification browser and step inspector."""

from __future__ import annotations

from typing import Any

from app.experiments.experiment_engine import experiment_engine
from app.experiments.experiment_loader import list_available_protocols
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ExperimentView(QWidget):
    """View to select, inspect, and execute BAS experiment protocols."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._available_protocols = []
        self._init_ui()
        self._load_protocols_list()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Protocol Selector Toolbar
        selector_frame = QFrame()
        selector_frame.setStyleSheet(
            "background-color: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 10px;"
        )
        s_layout = QHBoxLayout(selector_frame)

        lbl = QLabel("EXPERIMENT PROTOCOL:")
        lbl.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 11px;")
        self.protocol_combo = QComboBox()
        self.protocol_combo.setStyleSheet(
            "background-color: #1e293b; color: white; padding: 6px; border-radius: 4px; font-weight: bold;"
        )
        self.protocol_combo.currentIndexChanged.connect(self._on_protocol_selected)

        self.load_btn = QPushButton("LOAD SPECIFICATION")
        self.load_btn.setStyleSheet(
            "background-color: #0284c7; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;"
        )
        self.load_btn.clicked.connect(self._on_load_clicked)

        s_layout.addWidget(lbl)
        s_layout.addWidget(self.protocol_combo, stretch=1)
        s_layout.addWidget(self.load_btn)
        layout.addWidget(selector_frame)

        # Metadata Card
        self.meta_frame = QFrame()
        self.meta_frame.setStyleSheet(
            "background-color: #080c14; border: 1px solid #1e293b; border-radius: 6px; padding: 12px;"
        )
        m_layout = QVBoxLayout(self.meta_frame)
        self.title_lbl = QLabel("Title: -")
        self.title_lbl.setStyleSheet("color: #f8fafc; font-size: 14px; font-weight: bold;")
        self.agency_lbl = QLabel("Agency: ISRO HSFC | Node: BAS-SCIENCE-NODE-1 | Glovebox: GB-01")
        self.agency_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")

        m_layout.addWidget(self.title_lbl)
        m_layout.addWidget(self.agency_lbl)
        layout.addWidget(self.meta_frame)

        # Steps Table
        steps_lbl = QLabel("CANONICAL PROCEDURAL STEPS")
        steps_lbl.setStyleSheet(
            "color: #94a3b8; font-size: 11px; font-weight: 800; letter-spacing: 1px;"
        )
        layout.addWidget(steps_lbl)

        self.steps_table = QTableWidget(0, 5)
        self.steps_table.setHorizontalHeaderLabels(
            ["STEP #", "STEP ID", "DESCRIPTION", "EXPECTED ACTION", "STATUS"]
        )
        self.steps_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.steps_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.steps_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.steps_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.steps_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.steps_table.setStyleSheet("""
            QTableWidget {
                background-color: #080c14;
                color: #e2e8f0;
                gridline-color: #1e293b;
                border: 1px solid #1e293b;
                border-radius: 6px;
                font-family: monospace;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #94a3b8;
                border: 1px solid #1e293b;
                padding: 6px;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.steps_table, stretch=1)

    def _load_protocols_list(self) -> None:
        self._available_protocols = list_available_protocols()
        self.protocol_combo.clear()
        for p in self._available_protocols:
            self.protocol_combo.addItem(f"{p['experiment_id']}: {p['title']}", p["file_path"])

    def _on_protocol_selected(self, index: int) -> None:
        pass

    def _on_load_clicked(self) -> None:
        file_path = self.protocol_combo.currentData()
        if file_path:
            spec = experiment_engine.load_protocol_file(file_path)
            self._render_spec(spec)

    def _render_spec(self, spec: Any) -> None:
        self.title_lbl.setText(f"{spec.metadata.experiment_id}: {spec.metadata.title}")
        self.agency_lbl.setText(
            f"Agency: {spec.metadata.lead_agency} | Node: {spec.metadata.station_module} | Glovebox: {spec.metadata.glovebox_id}"
        )

        steps = spec.steps
        self.steps_table.setRowCount(len(steps))
        for r, s in enumerate(steps):
            exp_actions = ", ".join(s.expected_actions) if s.expected_actions else "execute"
            self.steps_table.setItem(r, 0, QTableWidgetItem(f"{s.step_number:02d}"))
            self.steps_table.setItem(r, 1, QTableWidgetItem(s.step_id))
            self.steps_table.setItem(r, 2, QTableWidgetItem(s.description))
            self.steps_table.setItem(r, 3, QTableWidgetItem(exp_actions))
            self.steps_table.setItem(r, 4, QTableWidgetItem("PENDING"))
