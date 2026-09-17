"""Deterministic 11-state protocol lifecycle Finite State Machine."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.exceptions import ProtocolStateError
from app.core.logging import get_logger
from app.experiments.experiment_schema import ExperimentSpecification, ExperimentStep

logger = get_logger("app.experiments.fsm")


class ProtocolState(StrEnum):
    """The 11 discrete states of the Protocol Lifecycle FSM."""

    IDLE = "IDLE"
    LOADED = "LOADED"
    PRECHECK = "PRECHECK"
    RUNNING = "RUNNING"
    STEP_IN_PROGRESS = "STEP_IN_PROGRESS"
    STEP_COMPLETED = "STEP_COMPLETED"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    DEGRADED = "DEGRADED"


class StateTransitionRecord(BaseModel):
    """Record of an FSM transition event."""

    transition_id: str = Field(default_factory=lambda: str(uuid4()))
    from_state: ProtocolState
    to_state: ProtocolState
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reason: str = ""
    step_id: str | None = None
    step_number: int | None = None


class ProtocolStateMachine:
    """Manages procedural execution lifecycle, step pointer, and state transitions."""

    VALID_TRANSITIONS: dict[ProtocolState, set[ProtocolState]] = {
        ProtocolState.IDLE: {ProtocolState.LOADED, ProtocolState.DEGRADED},
        ProtocolState.LOADED: {ProtocolState.PRECHECK, ProtocolState.RUNNING, ProtocolState.IDLE, ProtocolState.DEGRADED},
        ProtocolState.PRECHECK: {ProtocolState.RUNNING, ProtocolState.LOADED, ProtocolState.ABORTED, ProtocolState.DEGRADED},
        ProtocolState.RUNNING: {
            ProtocolState.STEP_IN_PROGRESS,
            ProtocolState.STEP_COMPLETED,
            ProtocolState.PAUSED,
            ProtocolState.BLOCKED,
            ProtocolState.COMPLETED,
            ProtocolState.ABORTED,
            ProtocolState.DEGRADED,
        },
        ProtocolState.STEP_IN_PROGRESS: {
            ProtocolState.STEP_IN_PROGRESS,
            ProtocolState.STEP_COMPLETED,
            ProtocolState.PAUSED,
            ProtocolState.BLOCKED,
            ProtocolState.COMPLETED,
            ProtocolState.ABORTED,
            ProtocolState.DEGRADED,
        },
        ProtocolState.STEP_COMPLETED: {
            ProtocolState.STEP_IN_PROGRESS,
            ProtocolState.RUNNING,
            ProtocolState.COMPLETED,
            ProtocolState.PAUSED,
            ProtocolState.ABORTED,
            ProtocolState.DEGRADED,
        },
        ProtocolState.PAUSED: {ProtocolState.RUNNING, ProtocolState.STEP_IN_PROGRESS, ProtocolState.ABORTED, ProtocolState.DEGRADED},
        ProtocolState.BLOCKED: {ProtocolState.RUNNING, ProtocolState.STEP_IN_PROGRESS, ProtocolState.ABORTED, ProtocolState.DEGRADED},
        ProtocolState.COMPLETED: {ProtocolState.IDLE, ProtocolState.LOADED},
        ProtocolState.ABORTED: {ProtocolState.IDLE, ProtocolState.LOADED},
        ProtocolState.DEGRADED: {ProtocolState.IDLE, ProtocolState.LOADED, ProtocolState.ABORTED},
    }

    def __init__(self) -> None:
        self._state: ProtocolState = ProtocolState.IDLE
        self._spec: ExperimentSpecification | None = None
        self._current_step_index: int = 0
        self._transition_history: list[StateTransitionRecord] = []
        self._step_start_time: datetime | None = None

    @property
    def state(self) -> ProtocolState:
        return self._state

    @property
    def spec(self) -> ExperimentSpecification | None:
        return self._spec

    @property
    def current_step_index(self) -> int:
        return self._current_step_index

    @property
    def current_step(self) -> ExperimentStep | None:
        if self._spec and 0 <= self._current_step_index < len(self._spec.steps):
            return self._spec.steps[self._current_step_index]
        return None

    def load_spec(self, spec: ExperimentSpecification) -> None:
        """Attach specification and transition to LOADED."""
        if self._state not in (ProtocolState.IDLE, ProtocolState.LOADED, ProtocolState.COMPLETED, ProtocolState.ABORTED, ProtocolState.DEGRADED):
            self.reset()
        self._spec = spec
        self._current_step_index = 0
        self._transition(ProtocolState.LOADED, reason=f"Loaded experiment {spec.metadata.experiment_id}")

    def start_execution(self) -> None:
        """Commence procedural execution."""
        if not self._spec:
            raise ProtocolStateError("Cannot start execution: No specification loaded.")
        self._current_step_index = 0
        self._step_start_time = datetime.now(UTC)
        self._transition(ProtocolState.RUNNING, reason="Mission experiment started")
        self._transition(ProtocolState.STEP_IN_PROGRESS, reason="First step in progress")

    def advance_step(self) -> bool:
        """Advance to next sequential step."""
        if not self._spec:
            return False

        self._transition(ProtocolState.STEP_COMPLETED, reason=f"Step {self._current_step_index + 1} completed")

        self._current_step_index += 1
        if self._current_step_index >= len(self._spec.steps):
            self._transition(ProtocolState.COMPLETED, reason="All protocol steps finalized")
            return True

        self._step_start_time = datetime.now(UTC)
        self._transition(ProtocolState.STEP_IN_PROGRESS, reason=f"Step {self._current_step_index + 1} started")
        return False

    def skip_to_step(self, target_index: int, reason: str = "Out of sequence skip") -> None:
        """Advance step pointer retroactively following validated skip."""
        if not self._spec or target_index >= len(self._spec.steps):
            return
        self._current_step_index = target_index
        self._step_start_time = datetime.now(UTC)
        self._transition(ProtocolState.STEP_IN_PROGRESS, reason=reason)

    def pause(self) -> None:
        self._transition(ProtocolState.PAUSED, reason="Experiment execution paused")

    def resume(self) -> None:
        self._transition(ProtocolState.STEP_IN_PROGRESS, reason="Experiment execution resumed")

    def abort(self, reason: str = "Operator abort") -> None:
        self._transition(ProtocolState.ABORTED, reason=reason)

    def reset(self) -> None:
        self._spec = None
        self._current_step_index = 0
        self._state = ProtocolState.IDLE
        self._transition_history.clear()

    def _transition(self, to_state: ProtocolState, reason: str = "") -> None:
        allowed = self.VALID_TRANSITIONS.get(self._state, set())
        if to_state not in allowed and to_state != self._state:
            raise ProtocolStateError(
                f"Invalid transition from {self._state.value} to {to_state.value}",
                details={"from": self._state.value, "to": to_state.value, "reason": reason},
            )

        curr_step = self.current_step
        record = StateTransitionRecord(
            from_state=self._state,
            to_state=to_state,
            reason=reason,
            step_id=curr_step.step_id if curr_step else None,
            step_number=curr_step.step_number if curr_step else None,
        )
        self._transition_history.append(record)
        old_state = self._state
        self._state = to_state
        logger.info("Protocol FSM transition", from_state=old_state.value, to_state=to_state.value, reason=reason)
