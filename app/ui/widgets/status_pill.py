"""Custom glowing status indicator pill widget for aerospace mission telemetry."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class StatusPill(QWidget):
    """Compact status pill with LED dot and bold label."""

    THEMES = {
        "green": ("#10b981", "rgba(16, 185, 129, 0.15)", "#34d399"),
        "cyan": ("#00e5ff", "rgba(0, 229, 255, 0.15)", "#38bdf8"),
        "yellow": ("#eab308", "rgba(234, 179, 8, 0.15)", "#fde047"),
        "red": ("#ef4444", "rgba(239, 68, 68, 0.15)", "#fca5a5"),
        "gray": ("#64748b", "rgba(100, 116, 139, 0.15)", "#94a3b8"),
    }

    def __init__(
        self, title: str, status: str = "READY", color: str = "green", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._status = status
        self._color = color

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(5)

        self._title_label = QLabel(f"{title}:")
        self._title_label.setStyleSheet(
            "color: #64748b; font-family: monospace; font-size: 10px; font-weight: 700;"
        )

        self._dot = QLabel("●")
        dot_color, _, _ = self.THEMES.get(color, self.THEMES["green"])
        self._dot.setStyleSheet(f"color: {dot_color}; font-size: 9px;")

        self._status_label = QLabel(status)
        _, _, text_color = self.THEMES.get(color, self.THEMES["green"])
        self._status_label.setStyleSheet(
            f"color: {text_color}; font-family: monospace; font-size: 10px; font-weight: 800; letter-spacing: 0.5px;"
        )

        layout.addWidget(self._title_label)
        layout.addWidget(self._dot)
        layout.addWidget(self._status_label)

        self._update_style()

    def set_status(self, status: str, color: str = "green") -> None:
        self._status = status
        self._color = color
        dot_color, _, text_color = self.THEMES.get(color, self.THEMES["green"])
        self._dot.setStyleSheet(f"color: {dot_color}; font-size: 9px;")
        self._status_label.setText(status)
        self._status_label.setStyleSheet(
            f"color: {text_color}; font-family: monospace; font-size: 10px; font-weight: 800; letter-spacing: 0.5px;"
        )
        self._update_style()

    def _update_style(self) -> None:
        self.setStyleSheet("""
            StatusPill {
                background-color: #060b14;
                border: 1px solid #111827;
                border-radius: 4px;
            }
        """)
