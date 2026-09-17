"""Custom glowing status indicator pill widget for aerospace mission telemetry."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class StatusPill(QWidget):
    """Compact status pill with LED dot and bold label."""

    THEMES = {
        "green": ("#10b981", "rgba(16, 185, 129, 0.2)", "#34d399"),
        "cyan": ("#06b6d4", "rgba(6, 182, 212, 0.2)", "#67e8f9"),
        "yellow": ("#eab308", "rgba(234, 179, 8, 0.2)", "#fde047"),
        "red": ("#ef4444", "rgba(239, 68, 68, 0.2)", "#fca5a5"),
        "gray": ("#64748b", "rgba(100, 116, 139, 0.2)", "#94a3b8"),
    }

    def __init__(self, title: str, status: str = "READY", color: str = "green", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._status = status
        self._color = color

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._title_label = QLabel(f"{title}:")
        self._title_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600;")

        self._dot = QLabel("●")
        self._dot.setStyleSheet(f"color: {self.THEMES.get(color, self.THEMES['green'])[0]}; font-size: 10px;")

        self._status_label = QLabel(status)
        self._status_label.setStyleSheet(f"color: {self.THEMES.get(color, self.THEMES['green'])[2]}; font-size: 11px; font-weight: 700;")

        layout.addWidget(self._title_label)
        layout.addWidget(self._dot)
        layout.addWidget(self._status_label)

        self._update_style()

    def set_status(self, status: str, color: str = "green") -> None:
        self._status = status
        self._color = color
        dot_color, _, text_color = self.THEMES.get(color, self.THEMES["green"])
        self._dot.setStyleSheet(f"color: {dot_color}; font-size: 10px;")
        self._status_label.setText(status)
        self._status_label.setStyleSheet(f"color: {text_color}; font-size: 11px; font-weight: 700;")
        self._update_style()

    def _update_style(self) -> None:
        _, bg_color, _ = self.THEMES.get(self._color, self.THEMES["green"])
        self.setStyleSheet(f"""
            StatusPill {{
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 6px;
            }}
        """)
