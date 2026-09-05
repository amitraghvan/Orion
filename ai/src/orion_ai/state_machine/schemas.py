"""Experiment state machine transition schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class StepCondition(BaseModel):
    """Precondition or postcondition predicate for an experiment step."""

    condition_type: Literal["OBJECT_DETECTED", "ACTIVITY_VERIFIED", "TIMEOUT", "MANUAL_OVERRIDE"]
    parameters: dict[str, Any]
    is_satisfied: bool = False


class TransitionRule(BaseModel):
    """Rule governing progression from one experiment step to the next."""

    from_step: str
    to_step: str
    required_conditions: list[StepCondition]
    timeout_seconds: float | None = None
    on_timeout_action: Literal["ALERT", "ABORT", "REPEAT"] = "ALERT"


class ExperimentStateSnapshot(BaseModel):
    """Current state machine progress status."""

    experiment_id: str
    run_id: str
    current_step: str
    step_elapsed_seconds: float
    is_completed: bool = False
    has_error: bool = False
    error_detail: str | None = None
    telemetry_state: dict[str, Any] = Field(default_factory=dict)
