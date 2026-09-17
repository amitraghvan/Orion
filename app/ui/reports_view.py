"""Post-mission scientific report browser and document viewer."""

from __future__ import annotations

from pathlib import Path

from app.core.paths import paths
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


class ReportsView(QWidget):
    """Inspects generated post-mission verification reports."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()
        self._refresh_reports()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Selector toolbar
        bar = QFrame()
        bar.setStyleSheet(
            "background-color: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 10px;"
        )
        b_layout = QHBoxLayout(bar)

        title = QLabel("SELECT MISSION REPORT:")
        title.setStyleSheet(
            "color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1px;"
        )
        b_layout.addWidget(title)

        self.report_combo = QComboBox()
        self.report_combo.setStyleSheet(
            "background-color: #1e293b; color: white; padding: 6px; border-radius: 4px; font-weight: bold;"
        )
        self.report_combo.currentIndexChanged.connect(self._on_report_selected)
        b_layout.addWidget(self.report_combo, stretch=1)

        ref_btn = QPushButton("REFRESH")
        ref_btn.setStyleSheet(
            "background-color: #1e293b; color: white; padding: 6px 14px; border-radius: 4px; font-weight: bold;"
        )
        ref_btn.clicked.connect(self._refresh_reports)
        b_layout.addWidget(ref_btn)

        layout.addWidget(bar)

        # Text Viewer
        self.text_browser = QTextBrowser()
        self.text_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #080c14;
                color: #e2e8f0;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 16px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        layout.addWidget(self.text_browser, stretch=1)

    def _refresh_reports(self) -> None:
        self.report_combo.clear()
        rep_dir = paths.reports_dir
        if rep_dir.is_dir():
            for md_file in sorted(rep_dir.glob("*.md"), reverse=True):
                self.report_combo.addItem(md_file.name, str(md_file))

        if self.report_combo.count() == 0:
            self.text_browser.setMarkdown(
                "# No Mission Reports Found\n\nRun an experiment to generate a scientific report."
            )
        else:
            self._on_report_selected(0)

    def _on_report_selected(self, index: int) -> None:
        file_path = self.report_combo.currentData()
        if file_path and Path(file_path).is_file():
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                self.text_browser.setMarkdown(content)
            except Exception as exc:
                self.text_browser.setPlainText(f"Error reading report: {exc}")
