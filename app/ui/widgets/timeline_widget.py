"""Horizontal graphical step progression timeline widget."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class StepTimelineWidget(QWidget):
    """Visualizes experiment sequence progression across canonical procedural steps."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(75)
        self.setStyleSheet(
            "background-color: #080c14; border: 1px solid #1e293b; border-radius: 8px;"
        )

        self._steps: list[dict[str, Any]] = []
        self._current_step_num: int = 1

    def set_steps(self, steps: list[dict[str, Any]], current_step_num: int = 1) -> None:
        self._steps = steps
        self._current_step_num = current_step_num
        self.update()

    def set_active_step(self, step_num: int) -> None:
        self._current_step_num = step_num
        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if not self._steps:
            painter.setPen(QColor("#64748b"))
            painter.drawText(
                self.rect(), Qt.AlignCenter, "No active experiment protocol steps loaded"
            )
            return

        w = self.width()
        h = self.height()
        n = len(self._steps)
        if n == 0:
            return

        spacing = w / (n + 1)
        cy = h / 2.0

        # Draw connecting line
        line_pen = QPen(QColor("#334155"), 2)
        painter.setPen(line_pen)
        painter.drawLine(QPointF(spacing, cy), QPointF(spacing * n, cy))

        # Completed line
        completed_count = min(self._current_step_num - 1, n)
        if completed_count > 0:
            comp_pen = QPen(QColor("#10b981"), 3)
            painter.setPen(comp_pen)
            painter.drawLine(QPointF(spacing, cy), QPointF(spacing * max(1, completed_count), cy))

        font_num = QFont("Helvetica", 9, QFont.Bold)
        font_lbl = QFont("Helvetica", 8)

        # Draw step nodes
        for idx, step in enumerate(self._steps):
            step_num = step.get("step_number", idx + 1)
            cx = spacing * (idx + 1)

            # Node color
            if step_num < self._current_step_num:
                node_brush = QBrush(QColor("#10b981"))  # Completed
                border_pen = QPen(QColor("#34d399"), 2)
                symbol = "✓"
                text_color = QColor("#10b981")
            elif step_num == self._current_step_num:
                node_brush = QBrush(QColor("#06b6d4"))  # Active
                border_pen = QPen(QColor("#38bdf8"), 3)
                symbol = f"{step_num}"
                text_color = QColor("#38bdf8")
            else:
                node_brush = QBrush(QColor("#1e293b"))  # Pending
                border_pen = QPen(QColor("#475569"), 1)
                symbol = f"{step_num}"
                text_color = QColor("#64748b")

            # Draw circle
            painter.setBrush(node_brush)
            painter.setPen(border_pen)
            painter.drawEllipse(QPointF(cx, cy - 6), 14, 14)

            # Draw symbol
            painter.setPen(QColor("#ffffff"))
            painter.setFont(font_num)
            painter.drawText(QRectF(cx - 14, cy - 20, 28, 28), Qt.AlignCenter, symbol)

            # Draw label
            painter.setFont(font_lbl)
            painter.setPen(text_color)
            desc = step.get("description", f"Step {step_num}")
            short_desc = (desc[:10] + "..") if len(desc) > 10 else desc
            painter.drawText(QRectF(cx - 40, cy + 12, 80, 20), Qt.AlignCenter, short_desc)
