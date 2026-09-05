"""State machine configuration schemas."""

from pydantic import BaseModel, Field


class StateMachineConfig(BaseModel):
    """Configuration contract for state machine runtime."""

    strict_ordering: bool = True
    allow_step_skipping: bool = False
    default_step_timeout_seconds: float = Field(default=300.0, ge=5.0)
    enforce_preconditions: bool = True
