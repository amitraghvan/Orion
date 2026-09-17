"""Dedicated Live Optical Vision view with interactive layer controls and input source switching."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.camera.camera_manager import camera_manager
from app.core.paths import paths
from app.core.state_manager import state_manager
from app.ui.widgets.video_widget import VideoViewportWidget


class LiveVisionView(QWidget):
    """Large viewport dedicated to computer vision perception inspection."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()
        self._setup_timer()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Control & Overlay Toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 6px;")
        t_layout = QHBoxLayout(toolbar)
        t_layout.setContentsMargins(10, 4, 10, 4)
        t_layout.setSpacing(16)

        # Source selection
        t_layout.addWidget(QLabel("SOURCE:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(["CAM01 (USB Default)", "Sample Replay Video", "Glovebox Microgravity Feed"])
        self.source_combo.setStyleSheet("background-color: #1e293b; color: white; padding: 4px; border-radius: 4px;")
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        t_layout.addWidget(self.source_combo)

        t_layout.addSpacing(16)
        t_layout.addWidget(QLabel("OVERLAYS:"))

        # Checkboxes
        self.chk_boxes = QCheckBox("Bounding Boxes")
        self.chk_boxes.setChecked(True)
        self.chk_boxes.toggled.connect(self._on_overlay_toggled)

        self.chk_skeleton = QCheckBox("Pose Skeleton")
        self.chk_skeleton.setChecked(True)
        self.chk_skeleton.toggled.connect(self._on_overlay_toggled)

        self.chk_hands = QCheckBox("Hands")
        self.chk_hands.setChecked(True)
        self.chk_hands.toggled.connect(self._on_overlay_toggled)

        self.chk_vectors = QCheckBox("Interaction Vectors")
        self.chk_vectors.setChecked(True)
        self.chk_vectors.toggled.connect(self._on_overlay_toggled)

        self.chk_hud = QCheckBox("Perception HUD")
        self.chk_hud.setChecked(True)
        self.chk_hud.toggled.connect(self._on_overlay_toggled)

        for chk in [self.chk_boxes, self.chk_skeleton, self.chk_hands, self.chk_vectors, self.chk_hud]:
            chk.setStyleSheet("color: #e2e8f0; font-size: 11px; font-weight: 600;")
            t_layout.addWidget(chk)

        t_layout.addStretch()
        layout.addWidget(toolbar)

        # Main video viewport
        self.video_widget = VideoViewportWidget()
        layout.addWidget(self.video_widget, stretch=1)

    def _setup_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_frame)
        self._timer.start(33)  # ~30 FPS

    def _refresh_frame(self) -> None:
        frame = camera_manager.latest_frame
        snapshot = state_manager.latest_perception
        hud = f"FPS: {camera_manager.actual_fps:.1f} | Frame: {snapshot.frame_index}\nAct: {snapshot.recognized_activity.upper()}"
        self.video_widget.update_frame(
            frame_bgr=frame,
            detections=snapshot.detected_objects,
            poses=snapshot.poses,
            hands=snapshot.hands,
            interactions=snapshot.interactions,
            hud_text=hud,
        )

    def _on_overlay_toggled(self) -> None:
        self.video_widget.show_boxes = self.chk_boxes.isChecked()
        self.video_widget.show_skeleton = self.chk_skeleton.isChecked()
        self.video_widget.show_hands = self.chk_hands.isChecked()
        self.video_widget.show_vectors = self.chk_vectors.isChecked()
        self.video_widget.show_hud = self.chk_hud.isChecked()
        self.video_widget.update()

    def _on_source_changed(self, index: int) -> None:
        if index == 1:
            # Sample replay video
            sample_path = paths.assets_dir / "sample_replay.mp4"
            camera_manager.stop()
            camera_manager.configure(str(sample_path), loop=True)
            camera_manager.start()
        elif index == 0:
            camera_manager.stop()
            camera_manager.configure("0", loop=False)
            camera_manager.start()
