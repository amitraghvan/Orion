"""Horizontal graphical step progression timeline widget for BAS experiment execution."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class StepTimelineWidget(QWidget):
    """Visualizes experiment sequence progression across canonical procedural steps."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(82)
        self.setStyleSheet(
            "background-color: #050811; border: 1px solid #1e293b; border-radius: 8px;"
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
            painter.setFont(QFont("Monospace", 10))
            painter.drawText(
                self.rect(), Qt.AlignCenter, "[ AWAITING EXPERIMENT PROTOCOL INITIALIZATION ]"
            )
            return

        w = float(self.width())
        h = float(self.height())
        n = len(self._steps)
        if n == 0:
            return

        slot_w = w / float(n)
        cy = 28.0

        # Background track line
        line_pen = QPen(QColor("#1e293b"), 3)
        painter.setPen(line_pen)
        start_x = slot_w * 0.5
        end_x = slot_w * (float(n) - 0.5)
        painter.drawLine(QPointF(start_x, cy), QPointF(end_x, cy))

        # Completed track line
        completed_count = min(self._current_step_num - 1, n)
        if completed_count > 0:
            comp_pen = QPen(QColor("#10b981"), 3)
            painter.setPen(comp_pen)
            active_end_x = slot_w * (float(completed_count) - 0.5)
            painter.drawLine(QPointF(start_x, cy), QPointF(active_end_x, cy))

        font_num = QFont("Monospace", 9, QFont.Bold)
        font_lbl = QFont("Monospace", 8, QFont.Bold)

        # Draw step milestones
        for idx, step in enumerate(self._steps):
            step_num = step.get("step_number", idx + 1)
            cx = slot_w * (float(idx) + 0.5)

            # Node styling based on progression
            if step_num < self._current_step_num:
                node_brush = QBrush(QColor("#064e3b"))
                border_pen = QPen(QColor("#10b981"), 2)
                symbol = "✓"
                text_color = QColor("#34d399")
            elif step_num == self._current_step_num:
                node_brush = QBrush(QColor("#0c4a6e"))
                border_pen = QPen(QColor("#00e5ff"), 2)
                symbol = f"{step_num:02d}"
                text_color = QColor("#00e5ff")
            else:
                node_brush = QBrush(QColor("#0b0f19"))
                border_pen = QPen(QColor("#334155"), 1)
                symbol = f"{step_num:02d}"
                text_color = QColor("#64748b")

            # Draw outer glow circle for active step
            if step_num == self._current_step_num:
                glow_pen = QPen(QColor(0, 229, 255, 60), 4)
                painter.setPen(glow_pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(cx, cy), 17, 17)

            # Draw milestone circle
            painter.setBrush(node_brush)
            painter.setPen(border_pen)
            painter.drawEllipse(QPointF(cx, cy), 13, 13)

            # Draw step number / checkmark
            painter.setPen(QColor("#ffffff"))
            painter.setFont(font_num)
            painter.drawText(QRectF(cx - 13, cy - 13, 26, 26), Qt.AlignCenter, symbol)

            # Draw step label
            painter.setFont(font_lbl)
            painter.setPen(text_color)
            desc = step.get("description", f"Step {step_num}")

            # Clean formatting for space-efficient display
            clean_desc = desc.replace("Pick up", "Pick").replace("Place down", "Place")
            lbl_rect = QRectF(cx - (slot_w * 0.48), cy + 16, slot_w * 0.96, 32)
            painter.drawText(lbl_rect, Qt.AlignHCenter | Qt.TextWordWrap, clean_desc)
