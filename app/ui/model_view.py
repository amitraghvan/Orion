"""AI Model Manager and inference benchmark inspector view."""

from __future__ import annotations

import numpy as np
from app.models.model_manager import model_manager
from PySide6.QtCore import QTimer
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


class ModelManagerView(QWidget):
    """Inspects loaded deep learning weights, backends, memory, and benchmark throughput."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()
        self._setup_timer()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Toolbar
        bar = QFrame()
        bar.setStyleSheet(
            "background-color: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 10px;"
        )
        b_layout = QHBoxLayout(bar)

        title = QLabel("AI MODEL REGISTRY & COMPUTE BACKENDS")
        title.setStyleSheet(
            "color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1px;"
        )
        b_layout.addWidget(title)
        b_layout.addStretch()

        self.bench_btn = QPushButton("EXECUTE BENCHMARK")
        self.bench_btn.setStyleSheet(
            "background-color: #3b0764; color: #d8b4fe; border: 1px solid #7c3aed; "
            "padding: 6px 14px; border-radius: 4px; font-family: monospace; font-size: 11px; font-weight: bold;"
        )
        self.bench_btn.clicked.connect(self._run_benchmarks)
        b_layout.addWidget(self.bench_btn)

        layout.addWidget(bar)

        # Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["MODEL", "BACKEND", "DEVICE", "WEIGHTS FILE", "STATUS", "LATENCY"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
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

    def _setup_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_table)
        self._timer.start(1000)

    def _refresh_table(self) -> None:
        overview = model_manager.get_status_overview()
        self.table.setRowCount(len(overview))
        for row, item in enumerate(overview):
            self.table.setItem(row, 0, QTableWidgetItem(item["name"].upper()))
            self.table.setItem(row, 1, QTableWidgetItem(item["backend"]))
            self.table.setItem(row, 2, QTableWidgetItem(item["device"]))
            self.table.setItem(row, 3, QTableWidgetItem(item["path"]))
            status_str = "READY" if item["loaded"] else "UNLOADED"
            self.table.setItem(row, 4, QTableWidgetItem(status_str))
            lat = f"{item['latency_ms']:.1f} ms" if item["latency_ms"] > 0 else "-"
            self.table.setItem(row, 5, QTableWidgetItem(lat))

    def _run_benchmarks(self) -> None:
        dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
        model_manager.benchmark_model("detection", dummy_frame, iterations=5)
        model_manager.benchmark_model("pose", dummy_frame, iterations=5)

        dummy_seq = np.zeros((1, 4, 32, 17), dtype=np.float32)
        model_manager.benchmark_model("activity", dummy_seq, iterations=10)
        self._refresh_table()
