"""High-performance computer vision viewport widget with GPU-accelerated QPainter overlays."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np
from app.intelligence.pose_estimator import COCO_BONES
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget


class VideoViewportWidget(QWidget):
    """Renders video frames and dynamic deep learning inference overlays with aerospace HUD."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(480, 270)
        self.setStyleSheet(
            "background-color: #030712; border: 1px solid #1e293b; border-radius: 8px;"
        )

        self._image: QImage | None = None
        self._detections: list[dict] = []
        self._poses: list[dict] = []
        self._hands: list[dict] = []
        self._interactions: list[dict] = []
        self._hud_text: str = ""

        # Overlay layer toggles
        self.show_boxes: bool = True
        self.show_skeleton: bool = True
        self.show_hands: bool = True
        self.show_vectors: bool = True
        self.show_hud: bool = True

    def update_frame(
        self,
        frame_bgr: np.ndarray | None,
        detections: list[dict] | None = None,
        poses: list[dict] | None = None,
        hands: list[dict] | None = None,
        interactions: list[dict] | None = None,
        hud_text: str = "",
    ) -> None:
        """Update frame buffer and trigger repaint."""
        if frame_bgr is not None and frame_bgr.size > 0:
            h, w, c = frame_bgr.shape
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            self._image = QImage(rgb.data, w, h, c * w, QImage.Format_RGB888).copy()
        else:
            self._image = None

        self._detections = detections or []
        self._poses = poses or []
        self._hands = hands or []
        self._interactions = interactions or []
        self._hud_text = hud_text

        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w_widget = self.width()
        h_widget = self.height()

        if self._image is None or self._image.isNull():
            # Render standby pattern
            painter.fillRect(0, 0, w_widget, h_widget, QColor("#030712"))
            painter.setPen(QColor("#1e293b"))

            # Draw subtle tactical grid lines
            for gx in range(40, w_widget, 60):
                painter.drawLine(gx, 0, gx, h_widget)
            for gy in range(40, h_widget, 60):
                painter.drawLine(0, gy, w_widget, gy)

            painter.setPen(QColor("#38bdf8"))
            font_title = QFont("Monospace", 12, QFont.Bold)
            painter.setFont(font_title)
            painter.drawText(
                self.rect().adjusted(0, -20, 0, -20),
                Qt.AlignCenter,
                "OPTICAL SENSOR FEED STANDBY",
            )
            painter.setPen(QColor("#64748b"))
            font_sub = QFont("Monospace", 10)
            painter.setFont(font_sub)
            painter.drawText(
                self.rect().adjusted(0, 25, 0, 25),
                Qt.AlignCenter,
                "[ CAM-01 OFFLINE • AWAITING VIDEO INPUT / HARDWARE PROBE ]",
            )
            return

        # Calculate aspect-ratio preserving dimensions
        img_w = self._image.width()
        img_h = self._image.height()
        scale = min(w_widget / img_w, h_widget / img_h)
        draw_w = img_w * scale
        draw_h = img_h * scale
        offset_x = (w_widget - draw_w) / 2.0
        offset_y = (h_widget - draw_h) / 2.0

        # Draw frame
        target_rect = QRectF(offset_x, offset_y, draw_w, draw_h)
        painter.drawImage(target_rect, self._image)

        # Draw tactical viewport corner brackets
        self._draw_viewport_corners(painter, offset_x, offset_y, draw_w, draw_h)

        # 1. Draw Skeleton Overlays
        if self.show_skeleton:
            self._draw_skeletons(painter, scale, offset_x, offset_y)

        # 2. Draw Object & Person Bounding Boxes
        if self.show_boxes:
            self._draw_bounding_boxes(painter, scale, offset_x, offset_y)

        # 3. Draw Hands
        if self.show_hands:
            self._draw_hands(painter, scale, offset_x, offset_y)

        # 4. Draw Interaction Vectors
        if self.show_vectors:
            self._draw_interaction_vectors(painter, scale, offset_x, offset_y)

        # 5. Draw On-Screen HUD Overlay
        if self.show_hud and self._hud_text:
            self._draw_hud(painter, offset_x, offset_y)

    def _draw_viewport_corners(
        self, painter: QPainter, ox: float, oy: float, w: float, h: float
    ) -> None:
        """Draw tactical corner reticles around video frame."""
        pen = QPen(QColor(6, 182, 212, 160), 2)
        painter.setPen(pen)
        b_len = 16.0

        # Top-Left
        painter.drawLine(QPointF(ox, oy), QPointF(ox + b_len, oy))
        painter.drawLine(QPointF(ox, oy), QPointF(ox, oy + b_len))
        # Top-Right
        painter.drawLine(QPointF(ox + w, oy), QPointF(ox + w - b_len, oy))
        painter.drawLine(QPointF(ox + w, oy), QPointF(ox + w, oy + b_len))
        # Bottom-Left
        painter.drawLine(QPointF(ox, oy + h), QPointF(ox + b_len, oy + h))
        painter.drawLine(QPointF(ox, oy + h), QPointF(ox, oy + h - b_len))
        # Bottom-Right
        painter.drawLine(QPointF(ox + w, oy + h), QPointF(ox + w - b_len, oy + h))
        painter.drawLine(QPointF(ox + w, oy + h), QPointF(ox + w, oy + h - b_len))

        # Center micro-crosshair
        cx = ox + w / 2.0
        cy = oy + h / 2.0
        c_pen = QPen(QColor(56, 189, 248, 80), 1)
        painter.setPen(c_pen)
        painter.drawLine(QPointF(cx - 8, cy), QPointF(cx + 8, cy))
        painter.drawLine(QPointF(cx, cy - 8), QPointF(cx, cy + 8))

    def _draw_skeletons(self, painter: QPainter, scale: float, ox: float, oy: float) -> None:
        bone_pen = QPen(QColor(56, 189, 248, 220), 2)
        joint_brush = QBrush(QColor(16, 185, 129, 240))

        painter.setPen(bone_pen)

        for pose in self._poses:
            kpts = pose.get("keypoints")
            if kpts is None or len(kpts) < 17:
                continue

            # Draw bones
            for u, v in COCO_BONES:
                if u < len(kpts) and v < len(kpts):
                    if kpts[u][2] > 0.25 and kpts[v][2] > 0.25:
                        x1 = kpts[u][0] * scale + ox
                        y1 = kpts[u][1] * scale + oy
                        x2 = kpts[v][0] * scale + ox
                        y2 = kpts[v][1] * scale + oy
                        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

            # Draw keypoint dots
            painter.setBrush(joint_brush)
            painter.setPen(Qt.NoPen)
            for j in range(len(kpts)):
                if kpts[j][2] > 0.25:
                    kx = kpts[j][0] * scale + ox
                    ky = kpts[j][1] * scale + oy
                    painter.drawEllipse(QPointF(kx, ky), 3.5, 3.5)

    def _draw_bounding_boxes(self, painter: QPainter, scale: float, ox: float, oy: float) -> None:
        font = QFont("Monospace", 9, QFont.Bold)
        painter.setFont(font)

        for obj in self._detections:
            box = obj.get("bbox", [0, 0, 0, 0])
            cname = obj.get("class_name", "object")
            conf = obj.get("confidence", 0.0)
            tid = obj.get("track_id", 0)

            x1 = box[0] * scale + ox
            y1 = box[1] * scale + oy
            w = (box[2] - box[0]) * scale
            h = (box[3] - box[1]) * scale

            # Choose color
            if "yellow" in cname.lower():
                box_color = QColor("#eab308")
                tag = "YELLOW_BOX"
            elif "red" in cname.lower():
                box_color = QColor("#ef4444")
                tag = "RED_BOX"
            elif "person" in cname.lower():
                box_color = QColor("#06b6d4")
                tag = "ASTRONAUT"
            else:
                box_color = QColor("#10b981")
                tag = cname.upper()

            # Draw tactical corner brackets instead of flat box
            pen = QPen(box_color, 2)
            painter.setPen(pen)
            c_len = min(12.0, w / 3.0, h / 3.0)

            # Top-Left corner
            painter.drawLine(QPointF(x1, y1), QPointF(x1 + c_len, y1))
            painter.drawLine(QPointF(x1, y1), QPointF(x1, y1 + c_len))
            # Top-Right corner
            painter.drawLine(QPointF(x1 + w, y1), QPointF(x1 + w - c_len, y1))
            painter.drawLine(QPointF(x1 + w, y1), QPointF(x1 + w, y1 + c_len))
            # Bottom-Left corner
            painter.drawLine(QPointF(x1, y1 + h), QPointF(x1 + c_len, y1 + h))
            painter.drawLine(QPointF(x1, y1 + h), QPointF(x1, y1 + h - c_len))
            # Bottom-Right corner
            painter.drawLine(QPointF(x1 + w, y1 + h), QPointF(x1 + w - c_len, y1 + h))
            painter.drawLine(QPointF(x1 + w, y1 + h), QPointF(x1 + w, y1 + h - c_len))

            # Draw subtle bounding box outline
            thin_pen = QPen(QColor(box_color.red(), box_color.green(), box_color.blue(), 70), 1)
            painter.setPen(thin_pen)
            painter.drawRect(QRectF(x1, y1, w, h))

            # Draw technical label banner
            label = (
                f"[ {tag} #{tid} | {conf * 100:.0f}% ]" if tid else f"[ {tag} | {conf * 100:.0f}% ]"
            )
            text_rect = painter.fontMetrics().boundingRect(label)
            badge_w = text_rect.width() + 8
            badge_h = 16

            badge_y = max(oy + 2, y1 - badge_h - 2)
            painter.fillRect(QRectF(x1, badge_y, badge_w, badge_h), QColor("#030712ee"))
            painter.setPen(QPen(box_color, 1))
            painter.drawRect(QRectF(x1, badge_y, badge_w, badge_h))

            painter.setPen(box_color)
            painter.drawText(QRectF(x1 + 4, badge_y + 1, badge_w, badge_h), Qt.AlignLeft, label)

    def _draw_hands(self, painter: QPainter, scale: float, ox: float, oy: float) -> None:
        hand_pen = QPen(QColor("#f59e0b"), 2, Qt.DashLine)
        painter.setPen(hand_pen)
        painter.setBrush(QColor(245, 158, 11, 35))

        for hand in self._hands:
            box = hand.get("bbox", [0, 0, 0, 0])
            x1 = box[0] * scale + ox
            y1 = box[1] * scale + oy
            w = (box[2] - box[0]) * scale
            h = (box[3] - box[1]) * scale
            painter.drawEllipse(QRectF(x1, y1, w, h))

    def _draw_interaction_vectors(
        self, painter: QPainter, scale: float, ox: float, oy: float
    ) -> None:
        vector_pen = QPen(QColor("#a855f7"), 2, Qt.DashDotLine)
        painter.setPen(vector_pen)

        for inter in self._interactions:
            vec = inter.get("vector")
            if vec and len(vec) >= 4:
                x1 = vec[0] * scale + ox
                y1 = vec[1] * scale + oy
                x2 = vec[2] * scale + ox
                y2 = vec[3] * scale + oy
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
                # Draw mid-point marker
                mx = (x1 + x2) / 2.0
                my = (y1 + y2) / 2.0
                painter.setBrush(QBrush(QColor("#a855f7")))
                painter.drawEllipse(QPointF(mx, my), 3.0, 3.0)

    def _draw_hud(self, painter: QPainter, ox: float, oy: float) -> None:
        """Render pristine multi-line aerospace HUD panel in top-left."""
        hud_lines = [line.strip() for line in self._hud_text.split("\n") if line.strip()]
        if not hud_lines:
            return

        font_hdr = QFont("Monospace", 8, QFont.Bold)
        font_body = QFont("Monospace", 8)

        hud_x = ox + 12
        hud_y = oy + 12
        box_w = 340
        box_h = 24 + len(hud_lines) * 16

        # Draw HUD dark glass container
        painter.fillRect(QRectF(hud_x, hud_y, box_w, box_h), QColor(3, 7, 18, 225))
        painter.setPen(QPen(QColor(56, 189, 248, 180), 1))
        painter.drawRect(QRectF(hud_x, hud_y, box_w, box_h))

        # Top cyan accent bar
        painter.fillRect(QRectF(hud_x, hud_y, box_w, 2), QColor("#06b6d4"))

        # Header
        painter.setFont(font_hdr)
        painter.setPen(QColor("#38bdf8"))
        painter.drawText(hud_x + 8, hud_y + 14, "ORION PERCEPTION TELEMETRY [CAM-01]")

        painter.setPen(QColor("#10b981"))
        painter.drawText(hud_x + box_w - 70, hud_y + 14, "AIRGAPPED")

        # Telemetry metrics rows
        painter.setFont(font_body)
        painter.setPen(QColor("#cbd5e1"))

        curr_y = hud_y + 30
        for line in hud_lines:
            painter.drawText(hud_x + 8, curr_y, line)
            curr_y += 16
