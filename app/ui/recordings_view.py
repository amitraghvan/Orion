"""Historical mission recordings browser and media inspector."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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

from app.recording.storage_manager import storage_manager


class RecordingsView(QWidget):
    """View to explore, inspect, and open locally recorded experiment sessions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()
        self._refresh_list()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Toolbar
        bar = QFrame()
        bar.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 10px;")
        b_layout = QHBoxLayout(bar)

        title = QLabel("LOCAL MISSION SESSION RECORDINGS")
        title.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
        b_layout.addWidget(title)
        b_layout.addStretch()

        ref_btn = QPushButton("REFRESH LIST")
        ref_btn.setStyleSheet("background-color: #1e293b; color: white; padding: 6px 12px; border-radius: 4px; font-weight: bold;")
        ref_btn.clicked.connect(self._refresh_list)
        b_layout.addWidget(ref_btn)
        layout.addWidget(bar)

        # Recordings Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["EXPERIMENT", "RUN ID", "START TIME", "DURATION", "ACTIONS"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setStyleSheet("""
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
        layout.addWidget(self.table, stretch=1)

    def _refresh_list(self) -> None:
        sessions = storage_manager.list_recorded_sessions()
        self.table.setRowCount(len(sessions))

        for row, s in enumerate(sessions):
            self.table.setItem(row, 0, QTableWidgetItem(s["experiment_id"]))
            self.table.setItem(row, 1, QTableWidgetItem(s["run_id"]))
            self.table.setItem(row, 2, QTableWidgetItem(s["start_time"]))
            self.table.setItem(row, 3, QTableWidgetItem(f"{s['duration_seconds']}s"))

            # Action button
            folder_path = s["session_dir"]
            btn = QPushButton("Open Folder")
            btn.setStyleSheet("background-color: #0284c7; color: white; padding: 4px; border-radius: 4px;")
            btn.clicked.connect(lambda _, p=folder_path: self._open_folder(p))
            self.table.setCellWidget(row, 4, btn)

    def _open_folder(self, path_str: str) -> None:
        if sys.platform == "darwin":
            subprocess.run(["open", path_str], check=False)
        elif sys.platform == "win32":
            os.startfile(path_str)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", path_str], check=False)
