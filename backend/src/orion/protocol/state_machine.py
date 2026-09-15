"""Deterministic 11-state protocol lifecycle Finite State Machine."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, Field

from orion.protocol.decision_engine import DecisionStatus, ProtocolDecision

if TYPE_CHECKING:
    from experiments.schemas import ExperimentSpecification, ExperimentStep


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
    """Record of a transition event within the FSM history."""

    transition_id: str = Field(default_factory=lambda: str(uuid4()))
    from_state: ProtocolState
    to_state: ProtocolState
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reason: str = ""
    step_id: str | None = None
    step_number: int | None = None


class ProtocolStateError(Exception):
    """Raised when an invalid state transition is attempted."""


class ProtocolStateMachine:
    """Manages procedural execution lifecycle, step pointer, and state transitions."""

    # Valid transitions mapping
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
        ProtocolState.PAUSED: {
            ProtocolState.RUNNING,
            ProtocolState.STEP_IN_PROGRESS,
            ProtocolState.ABORTED,
            ProtocolState.DEGRADED,
        },
        ProtocolState.BLOCKED: {
            ProtocolState.RUNNING,
            ProtocolState.STEP_IN_PROGRESS,
            ProtocolState.STEP_COMPLETED,
            ProtocolState.ABORTED,
            ProtocolState.DEGRADED,
        },
        ProtocolState.COMPLETED: {ProtocolState.IDLE, ProtocolState.LOADED, ProtocolState.RUNNING, ProtocolState.DEGRADED},
        ProtocolState.ABORTED: {ProtocolState.IDLE, ProtocolState.LOADED, ProtocolState.RUNNING, ProtocolState.DEGRADED},
        ProtocolState.DEGRADED: {ProtocolState.IDLE, ProtocolState.LOADED, ProtocolState.RUNNING},
    }

    def __init__(self) -> None:
        self._state: ProtocolState = ProtocolState.IDLE
        self._spec: ExperimentSpecification | None = None
        self._run_id: str | None = None
        self._current_step_index: int = 0
        self._actor_track_id: int | None = None
        self._history: list[StateTransitionRecord] = []
        self._step_start_time: datetime | None = None

    @property
    def state(self) -> ProtocolState:
        return self._state

    @property
    def spec(self) -> ExperimentSpecification | None:
        return self._spec

    @property
    def run_id(self) -> str | None:
        return self._run_id

    @property
    def current_step_index(self) -> int:
        return self._current_step_index

    @property
    def actor_track_id(self) -> int | None:
        return self._actor_track_id

    @property
    def history(self) -> list[StateTransitionRecord]:
        return list(self._history)

    @property
    def current_step(self) -> ExperimentStep | None:
        if self._spec and 0 <= self._current_step_index < len(self._spec.steps):
            return self._spec.steps[self._current_step_index]
        return None

    def _transition_to(self, new_state: ProtocolState, reason: str = "") -> None:
        """Execute and record state transition if valid."""
        allowed = self.VALID_TRANSITIONS.get(self._state, set())
        if new_state not in allowed:
            raise ProtocolStateError(
                f"Invalid transition from {self._state.value} to {new_state.value}. (Reason: {reason})"
            )

        step = self.current_step
        record = StateTransitionRecord(
            from_state=self._state,
            to_state=new_state,
            reason=reason,
            step_id=step.step_id if step else None,
            step_number=step.step_number if step else None,
        )
        self._history.append(record)
        self._state = new_state

    def load_protocol(self, spec: ExperimentSpecification) -> None:
        """Load an ExperimentSpecification into the FSM."""
        self._transition_to(ProtocolState.LOADED, reason=f"Loaded protocol {spec.metadata.experiment_id}")
        self._spec = spec
        self._current_step_index = 0
        self._run_id = None
        self._actor_track_id = None
        self._step_start_time = None

    def start_precheck(self) -> None:
        """Move from LOADED to PRECHECK."""
        self._transition_to(ProtocolState.PRECHECK, reason="Beginning workstation and hardware precheck")

    def start_run(self, run_id: str, actor_track_id: int | None = None) -> None:
        """Initialize an experiment execution run."""
        if not self._spec:
            raise ProtocolStateError("Cannot start run without a loaded experiment protocol")

        self._run_id = run_id
        self._actor_track_id = actor_track_id
        self._current_step_index = 0
        self._step_start_time = datetime.now(UTC)
        self._transition_to(ProtocolState.RUNNING, reason=f"Started run {run_id}")

    def pause(self, reason: str = "Operator paused execution") -> None:
        """Pause active experiment execution."""
        self._transition_to(ProtocolState.PAUSED, reason=reason)

    def resume(self, reason: str = "Operator resumed execution") -> None:
        """Resume paused experiment execution."""
        self._transition_to(ProtocolState.RUNNING, reason=reason)

    def abort(self, reason: str = "Operator aborted experiment") -> None:
        """Permanently abort active experiment run."""
        self._transition_to(ProtocolState.ABORTED, reason=reason)

    def mark_degraded(self, error: str) -> None:
        """Safely transition to DEGRADED mode on internal fault."""
        self._transition_to(ProtocolState.DEGRADED, reason=f"Degraded fault: {error}")

    def reset_to_idle(self) -> None:
        """Reset state machine back to IDLE."""
        self._transition_to(ProtocolState.IDLE, reason="Manual reset to IDLE")
        self._spec = None
        self._run_id = None
        self._current_step_index = 0
        self._actor_track_id = None
        self._step_start_time = None

    def advance_step(self) -> bool:
        """Advance to the next step if available, or mark COMPLETED."""
        if not self._spec:
            return False

        if self._current_step_index + 1 < len(self._spec.steps):
            self._current_step_index += 1
            self._step_start_time = datetime.now(UTC)
            self._transition_to(
                ProtocolState.STEP_IN_PROGRESS,
                reason=f"Advanced to step {self._spec.steps[self._current_step_index].step_id}",
            )
            return True
        self._transition_to(ProtocolState.COMPLETED, reason="All protocol steps completed successfully")
        return False

    def skip_to_step(self, target_step_id: str, reason: str = "Operator jump") -> bool:
        """Directly jump to a designated step by ID."""
        if not self._spec:
            return False

        for idx, s in enumerate(self._spec.steps):
            if s.step_id == target_step_id:
                self._current_step_index = idx
                self._step_start_time = datetime.now(UTC)
                self._transition_to(
                    ProtocolState.STEP_IN_PROGRESS,
                    reason=f"{reason}: jumped to {target_step_id}",
                )
                return True
        return False

    def resolve_blocked(self, resolution: str) -> None:
        """Resolve a BLOCKED deviation state."""
        if self._state != ProtocolState.BLOCKED:
            return

        res = resolution.upper().strip()
        if res == "PROCEED":
            self.advance_step()
        elif res == "RETRY":
            self._step_start_time = datetime.now(UTC)
            self._transition_to(ProtocolState.STEP_IN_PROGRESS, reason="Operator requested step retry")
        elif res == "ABORT":
            self.abort(reason="Operator chose to abort on blocked deviation")
        else:
            self._transition_to(ProtocolState.RUNNING, reason=f"Resolved blocked: {resolution}")

    def process_decision(self, decision: ProtocolDecision) -> None:
        """Update FSM state based on an evaluated ProtocolDecision."""
        if self._state in (ProtocolState.IDLE, ProtocolState.LOADED, ProtocolState.PRECHECK, ProtocolState.PAUSED, ProtocolState.COMPLETED, ProtocolState.ABORTED, ProtocolState.DEGRADED):
            return

        status = decision.status

        if status == DecisionStatus.VALID:
            # Current step is successfully completed
            self._transition_to(ProtocolState.STEP_COMPLETED, reason=f"Valid step execution: {decision.explanation}")
            # Automatically advance or complete
            self.advance_step()

        elif status in (
            DecisionStatus.OUT_OF_SEQUENCE,
            DecisionStatus.SKIPPED,
            DecisionStatus.WRONG_OBJECT,
            DecisionStatus.INTERRUPTED,
            DecisionStatus.TIMEOUT,
            DecisionStatus.INVALID_ACTION,
        ):
            self._transition_to(ProtocolState.BLOCKED, reason=f"Deviation ({status.value}): {decision.explanation}")

        elif status == DecisionStatus.WAITING_FOR_EVIDENCE:
            if self._state == ProtocolState.RUNNING and decision.debounce_count > 0:
                self._transition_to(ProtocolState.STEP_IN_PROGRESS, reason="Action observed; step in progress")

        elif status == DecisionStatus.STEP_UNCERTAIN:
            # Maintain active progress without blocking or passing
            pass
