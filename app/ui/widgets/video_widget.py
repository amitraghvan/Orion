"""High-performance computer vision viewport widget with GPU-accelerated QPainter overlays."""

from __future__ import annotations

import cv2
import numpy as np
from app.intelligence.pose_estimator import COCO_BONES
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget


class VideoViewportWidget(QWidget):
    """Renders video frames and dynamic deep learning inference overlays."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(480, 270)
        self.setStyleSheet("background-color: #050811; border-radius: 8px;")

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
            painter.fillRect(0, 0, w_widget, h_widget, QColor("#080c14"))
            painter.setPen(QColor("#475569"))
            font = QFont("Helvetica", 13, QFont.Bold)
            painter.setFont(font)
            painter.drawText(
                self.rect(), Qt.AlignCenter, "OPTICAL SENSOR FEED OFFLINE\nAwaiting video input"
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
            self._draw_hud(painter)

    def _draw_skeletons(self, painter: QPainter, scale: float, ox: float, oy: float) -> None:
        bone_pen = QPen(QColor(6, 182, 212, 200), 2)
        joint_brush = QBrush(QColor(16, 185, 129, 230))

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
                    painter.drawEllipse(QPointF(kx, ky), 3.0, 3.0)

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
            elif "red" in cname.lower():
                box_color = QColor("#ef4444")
            elif "person" in cname.lower():
                box_color = QColor("#06b6d4")
            else:
                box_color = QColor("#10b981")

            # Draw box
            pen = QPen(box_color, 2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(QRectF(x1, y1, w, h))

            # Draw label banner
            label = (
                f"{cname.upper()} #{tid} ({conf * 100:.0f}%)"
                if tid
                else f"{cname.upper()} ({conf * 100:.0f}%)"
            )
            text_rect = painter.fontMetrics().boundingRect(label)
            badge_w = text_rect.width() + 10
            badge_h = text_rect.height() + 4

            painter.fillRect(QRectF(x1, max(oy, y1 - badge_h), badge_w, badge_h), box_color)
            painter.setPen(QColor("#080c14"))
            painter.drawText(QRectF(x1 + 5, max(oy, y1 - badge_h) + 2, badge_w, badge_h), label)

    def _draw_hands(self, painter: QPainter, scale: float, ox: float, oy: float) -> None:
        hand_pen = QPen(QColor("#f59e0b"), 2, Qt.DashLine)
        painter.setPen(hand_pen)
        painter.setBrush(QColor(245, 158, 11, 40))

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
        vector_pen = QPen(QColor("#a855f7"), 2, Qt.SolidLine)
        painter.setPen(vector_pen)

        for inter in self._interactions:
            vec = inter.get("vector")
            if vec and len(vec) >= 4:
                x1 = vec[0] * scale + ox
                y1 = vec[1] * scale + oy
                x2 = vec[2] * scale + ox
                y2 = vec[3] * scale + oy
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_hud(self, painter: QPainter) -> None:
        painter.fillRect(15, 15, 220, 48, QColor(15, 23, 42, 200))
        painter.setPen(QColor("#38bdf8"))
        font = QFont("Monospace", 9, QFont.Bold)
        painter.setFont(font)
        painter.drawText(25, 33, "ORION PERCEPTION HUD")
        painter.setPen(QColor("#94a3b8"))
        painter.drawText(25, 50, self._hud_text)
