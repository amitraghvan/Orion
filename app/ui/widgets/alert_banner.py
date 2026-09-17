"""Active protocol deviation and alarm banner widget."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget


class AlertBanner(QFrame):
    """Emergency protocol deviation banner with alert severity styles and dismiss control."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AlertBanner")
        self.setVisible(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        self._icon = QLabel("⚠️")
        self._icon.setStyleSheet("font-size: 18px;")

        self._text_label = QLabel("PROTOCOL VIOLATION DETECTED")
        self._text_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #fecaca;")
        self._text_label.setWordWrap(True)

        self._ack_btn = QPushButton("ACKNOWLEDGE")
        self._ack_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: #ffffff;
                border: 1px solid #ef4444;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
        """)
        self._ack_btn.clicked.connect(self.dismiss)

        layout.addWidget(self._icon)
        layout.addWidget(self._text_label, stretch=1)
        layout.addWidget(self._ack_btn)

    def show_alert(self, message: str, severity: str = "WARNING") -> None:
        self._text_label.setText(f"[{severity}] {message}")
        if severity == "CRITICAL":
            self.setStyleSheet("""
                #AlertBanner {
                    background-color: #7f1d1d;
                    border: 2px solid #ef4444;
                    border-radius: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                #AlertBanner {
                    background-color: #450a0a;
                    border: 1px solid #dc2626;
                    border-radius: 6px;
                }
            """)
        self.setVisible(True)

    def dismiss(self) -> None:
        self.setVisible(False)
