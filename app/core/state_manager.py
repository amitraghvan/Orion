"""Thread-safe centralized state manager for ORION Desktop System."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger("app.core.state_manager")


class ApplicationState(StrEnum):
    """Lifecycle states of the desktop application."""

    INITIALIZING = "INITIALIZING"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    WARNING = "WARNING"
    ERROR = "ERROR"
    COMPLETED = "COMPLETED"
    SHUTDOWN = "SHUTDOWN"


class HardwareTelemetry(BaseModel):
    """Live system and hardware resource metrics."""

    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    gpu_percent: float = 0.0
    vram_percent: float = 0.0
    cuda_available: bool = False
    tensorrt_available: bool = False
    active_device: str = "CPU"
    camera_connected: bool = False
    camera_fps: float = 0.0
    inference_fps: float = 0.0
    inference_latency_ms: float = 0.0
    total_frames_processed: int = 0
    dropped_frames: int = 0
    queue_depth: int = 0


class PerceptionSnapshot(BaseModel):
    """Latest high-level perception frame output."""

    frame_index: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    detected_objects: list[dict[str, Any]] = Field(default_factory=list)
    poses: list[dict[str, Any]] = Field(default_factory=list)
    hands: list[dict[str, Any]] = Field(default_factory=list)
    interactions: list[dict[str, Any]] = Field(default_factory=list)
    recognized_activity: str = "idle"
    activity_confidence: float = 0.0
    activity_entropy: float = 0.0
    uncertainty_status: str = "NOMINAL"


class StateManager:
    """Observable thread-safe application state repository."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._app_state: ApplicationState = ApplicationState.INITIALIZING
        self._telemetry: HardwareTelemetry = HardwareTelemetry()
        self._latest_perception: PerceptionSnapshot = PerceptionSnapshot()

        # Active mission state
        self._active_experiment_id: str | None = None
        self._active_run_id: str | None = None
        self._protocol_fsm_state: str = "IDLE"
        self._current_step_number: int = 1
        self._current_step_id: str = ""
        self._current_step_name: str = ""
        self._total_steps: int = 0
        self._expected_action: str = ""
        self._detected_action: str = "idle"
        self._action_confidence: float = 0.0
        self._sequence_status: str = "VALID"
        self._next_step_text: str = ""
        self._next_step_action: str = ""
        self._is_recording: bool = False
        self._is_streaming: bool = False
        self._active_alerts: list[dict[str, Any]] = []

        self._listeners: list[Callable[[str, Any], None]] = []

    @property
    def app_state(self) -> ApplicationState:
        with self._lock:
            return self._app_state

    def set_app_state(self, new_state: ApplicationState) -> None:
        """Update application lifecycle state."""
        with self._lock:
            if self._app_state != new_state:
                old = self._app_state
                self._app_state = new_state
                logger.info(
                    "Application state changed", old_state=old.value, new_state=new_state.value
                )
                self._notify_listeners("app_state", new_state)

    @property
    def telemetry(self) -> HardwareTelemetry:
        with self._lock:
            return self._telemetry.model_copy()

    def update_telemetry(self, **kwargs: Any) -> None:
        """Update hardware telemetry attributes."""
        with self._lock:
            data = self._telemetry.model_dump()
            data.update(kwargs)
            self._telemetry = HardwareTelemetry.model_validate(data)
            self._notify_listeners("telemetry", self._telemetry)

    @property
    def latest_perception(self) -> PerceptionSnapshot:
        with self._lock:
            return self._latest_perception.model_copy()

    def set_perception_snapshot(self, snapshot: PerceptionSnapshot) -> None:
        """Update latest AI perception snapshot."""
        with self._lock:
            self._latest_perception = snapshot
            self._notify_listeners("perception", snapshot)

    def set_experiment_status(
        self,
        experiment_id: str,
        run_id: str,
        fsm_state: str,
        step_number: int,
        step_id: str,
        step_name: str,
        total_steps: int,
        expected_action: str,
    ) -> None:
        """Update experiment execution status."""
        with self._lock:
            self._active_experiment_id = experiment_id
            self._active_run_id = run_id
            self._protocol_fsm_state = fsm_state
            self._current_step_number = step_number
            self._current_step_id = step_id
            self._current_step_name = step_name
            self._total_steps = total_steps
            self._expected_action = expected_action
            self._notify_listeners(
                "experiment_status",
                {
                    "experiment_id": experiment_id,
                    "run_id": run_id,
                    "fsm_state": fsm_state,
                    "step_number": step_number,
                    "step_id": step_id,
                    "step_name": step_name,
                    "total_steps": total_steps,
                    "expected_action": expected_action,
                },
            )

    def set_guidance(self, next_step_text: str, next_step_action: str) -> None:
        """Update next step guidance."""
        with self._lock:
            self._next_step_text = next_step_text
            self._next_step_action = next_step_action
            self._notify_listeners(
                "guidance",
                {
                    "next_step_text": next_step_text,
                    "next_step_action": next_step_action,
                },
            )

    def set_decision_status(
        self,
        detected_action: str,
        confidence: float,
        sequence_status: str,
    ) -> None:
        """Update sequence decision status."""
        with self._lock:
            self._detected_action = detected_action
            self._action_confidence = confidence
            self._sequence_status = sequence_status
            self._notify_listeners(
                "decision",
                {
                    "detected_action": detected_action,
                    "confidence": confidence,
                    "sequence_status": sequence_status,
                },
            )

    def set_recording(self, recording: bool) -> None:
        with self._lock:
            self._is_recording = recording
            self._notify_listeners("recording", recording)

    def set_streaming(self, streaming: bool) -> None:
        with self._lock:
            self._is_streaming = streaming
            self._notify_listeners("streaming", streaming)

    def add_listener(self, listener: Callable[[str, Any], None]) -> Callable[[], None]:
        """Register a state change listener."""
        with self._lock:
            self._listeners.append(listener)

        def _remove() -> None:
            with self._lock:
                if listener in self._listeners:
                    self._listeners.remove(listener)

        return _remove

    def _notify_listeners(self, field: str, value: Any) -> None:
        for listener in list(self._listeners):
            try:
                listener(field, value)
            except Exception as exc:
                logger.error("State change listener exception", error=str(exc))


# Global state manager singleton
state_manager = StateManager()
