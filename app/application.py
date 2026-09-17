"""Application coordinator linking camera, intelligence, protocol engine, and GUI."""

from __future__ import annotations

import sys
import threading

import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from app.audio.tts_engine import tts_engine
from app.camera.camera_manager import camera_manager
from app.core.config import get_config
from app.core.lifecycle import lifecycle
from app.core.logging import get_logger
from app.core.paths import paths
from app.core.state_manager import state_manager
from app.database.database import db_manager
from app.experiments.experiment_engine import experiment_engine
from app.intelligence.intelligence_engine import intelligence_engine
from app.recording.recorder import experiment_recorder
from app.streaming.stream_manager import stream_manager
from app.ui.main_window import MainWindow

logger = get_logger("app.application")


class FrameDispatcher(QObject):
    """Qt signal emitter to transfer background CV frames to the GUI thread safely."""

    frame_ready = Signal(object, object, object, object, object, str)


class OrionApplication:
    """Master application coordinator managing desktop startup, loops, and shutdown."""

    def __init__(
        self,
        demo_mode: bool = False,
        video_override: str | None = None,
        camera_source: str | None = None,
        protocol_path: str | None = None,
    ) -> None:
        self.demo_mode = demo_mode
        self.video_override = video_override
        self.camera_source = camera_source
        self.protocol_path = protocol_path

        self.qt_app: QApplication = QApplication.instance() or QApplication(sys.argv)
        self.qt_app.setApplicationName("ORION BAS AI Copilot")
        self.qt_app.setOrganizationName("ISRO")

        self.main_window: MainWindow | None = None
        self.dispatcher = FrameDispatcher()

    def stop(self) -> None:
        """Gracefully shut down background threads and quit Qt loop."""
        camera_manager.stop()
        tts_engine.stop()
        stream_manager.stop()
        experiment_recorder.stop_recording()
        if self.qt_app is not None:
            self.qt_app.quit()

    def run(self) -> int:
        """Commence desktop application."""
        # 1. System Startup
        lifecycle.startup()

        # 2. Database
        db_manager.initialize()

        # 3. Audio TTS
        tts_engine.initialize()

        # 4. AI Perception Models
        intelligence_engine.initialize_models()

        # 5. Load Protocol
        cfg = get_config()
        proto_file = self.protocol_path or cfg.experiment.default_protocol
        try:
            experiment_engine.load_protocol_file(proto_file)
        except Exception as exc:
            logger.warning("Could not load protocol", path=proto_file, error=str(exc))

        # 6. Initialize GUI
        self.main_window = MainWindow()

        # Connect frame dispatcher signal to GUI video widgets
        self.dispatcher.frame_ready.connect(self._on_gui_frame)

        # 7. Configure Camera
        raw_source = cfg.camera.source
        if self.demo_mode or cfg.system.mode == "demo":
            sample_vid = paths.assets_dir / "sample_replay.mp4"
            raw_source = str(sample_vid)
            logger.info("Demo mode enabled: Using replay video source", source=raw_source)
        elif self.video_override:
            raw_source = self.video_override
        elif self.camera_source is not None:
            raw_source = self.camera_source

        # Parse numeric camera index to int for direct hardware acquisition
        source: str | int = (
            int(str(raw_source).strip()) if str(raw_source).strip().isdigit() else raw_source
        )

        camera_manager.configure(
            source=source,
            width=cfg.camera.width,
            height=cfg.camera.height,
            fps=cfg.camera.fps,
            loop=True,
        )
        success = camera_manager.start()
        if not success:
            logger.warning(
                "Failed to open requested camera source; falling back to sample replay video",
                source=source,
            )
            sample_vid = paths.assets_dir / "sample_replay.mp4"
            camera_manager.configure(
                source=str(sample_vid),
                width=cfg.camera.width,
                height=cfg.camera.height,
                fps=cfg.camera.fps,
                loop=True,
            )
            camera_manager.start()

        # Connect raw 30 FPS capture stream directly to recorder (decoupled from inference)
        camera_manager.add_frame_listener(
            lambda frame, frame_id, sensor_time: experiment_recorder.push_frame(frame)
        )

        # 8. Start Decoupled Inference Worker
        self._inference_running = True
        self._last_processed_frame_id = -1
        self._inference_thread = threading.Thread(
            target=self._inference_worker,
            name="InferenceConsumerWorker",
            daemon=True,
        )
        self._inference_thread.start()

        # 9. Start Optional IP Streaming
        if cfg.streaming.enabled:
            stream_manager.start(
                mode=cfg.streaming.mode,
                destination_ip=cfg.streaming.destination_ip,
                destination_port=cfg.streaming.destination_port,
                host=cfg.streaming.host,
                port=cfg.streaming.port,
            )

        # 10. Register Clean Shutdown Hooks
        lifecycle.register_shutdown_hook(self._stop_inference)
        lifecycle.register_shutdown_hook(camera_manager.stop)
        lifecycle.register_shutdown_hook(tts_engine.stop)
        lifecycle.register_shutdown_hook(stream_manager.stop)
        lifecycle.register_shutdown_hook(experiment_recorder.stop_recording)

        self.main_window.show()
        return self.qt_app.exec()

    def _stop_inference(self) -> None:
        """Halt inference consumer worker."""
        self._inference_running = False
        if (
            hasattr(self, "_inference_thread")
            and self._inference_thread
            and self._inference_thread.is_alive()
        ):
            self._inference_thread.join(timeout=1.0)

    def _inference_worker(self) -> None:
        """Dedicated background inference consumer processing newest frames from FrameBuffer."""
        import time

        while self._inference_running:
            try:
                frame_bgr = camera_manager.latest_frame
                frame_id = camera_manager.frame_id
                if frame_bgr is None or frame_id == self._last_processed_frame_id:
                    time.sleep(0.005)
                    continue

                self._last_processed_frame_id = frame_id
                timestamp = time.monotonic()

                # 1. Run Intelligence Pipeline on newest useful frame
                snapshot = intelligence_engine.process_frame(frame_bgr, frame_id, timestamp)
                latency_ms = (time.monotonic() - timestamp) * 1000.0

                # Update Telemetry so Top Status Pill CAM01 stays CONNECTED / STREAMING
                state_manager.update_telemetry(
                    camera_connected=True,
                    camera_fps=camera_manager.actual_fps,
                    inference_latency_ms=latency_ms,
                )

                # 2. Route Observation to Protocol Engine
                if experiment_engine.is_running:
                    experiment_engine.process_observation(
                        activity_label=snapshot.recognized_activity,
                        confidence=snapshot.activity_confidence,
                        entropy=snapshot.activity_entropy,
                    )

                # 3. IP Streaming Frame Push
                if stream_manager.is_running:
                    stream_manager.update_frame(frame_bgr)

                # 4. Emit thread-safe Signal to Qt GUI
                hud_text = (
                    f"FPS: {camera_manager.actual_fps:.1f} | LAT: {latency_ms:.1f}ms | FRAME: #{frame_id:06d}\n"
                    f"HAR: {snapshot.recognized_activity.upper()} ({snapshot.activity_confidence * 100:.0f}%) | "
                    f"ENTROPY: {snapshot.activity_entropy:.2f} | OBJS: {len(snapshot.detected_objects)}"
                )
                try:
                    self.dispatcher.frame_ready.emit(
                        frame_bgr,
                        snapshot.detected_objects,
                        snapshot.poses,
                        snapshot.hands,
                        snapshot.interactions,
                        hud_text,
                    )
                except RuntimeError:
                    break
            except Exception as exc:
                logger.warning("Inference worker loop caught exception", error=str(exc))
                time.sleep(0.01)

    def _on_gui_frame(
        self,
        frame_bgr: np.ndarray,
        detections: list[dict],
        poses: list[dict],
        hands: list[dict],
        interactions: list[dict],
        hud_text: str,
    ) -> None:
        """Executed on main Qt GUI thread."""
        if self.main_window is not None:
            self.main_window.dashboard_view.video_widget.update_frame(
                frame_bgr=frame_bgr,
                detections=detections,
                poses=poses,
                hands=hands,
                interactions=interactions,
                hud_text=hud_text,
            )
            # If live view is active, update it too
            if self.main_window.stack.currentIndex() == 1:
                self.main_window.live_view.video_widget.update_frame(
                    frame_bgr=frame_bgr,
                    detections=detections,
                    poses=poses,
                    hands=hands,
                    interactions=interactions,
                    hud_text=hud_text,
                )
