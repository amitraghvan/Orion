"""Pydantic v2 schemas for parsing and validating BAS experiment specifications."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ExperimentMetadata(BaseModel):
    """Scientific experiment metadata and lead investigator information."""

    experiment_id: str
    title: str
    principal_investigator: str
    lead_agency: str = "ISRO HSFC"
    station_module: str
    glovebox_id: str
    revision: str = "1.0"
    date_approved: str
    safety_classification: str = "LEVEL-1-NON-HAZARDOUS"


class ExperimentObject(BaseModel):
    """Tool, reagent, or hardware target required by the experiment."""

    object_id: str
    label: str
    required: bool = True
    expected_detection_model: str
    min_confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class StepTimeouts(BaseModel):
    """Nominal and max allowed durations for an experiment step."""

    nominal_duration_seconds: int = Field(ge=1)
    max_timeout_seconds: int = Field(ge=1)


class StepThresholds(BaseModel):
    """Perception thresholds required to satisfy step completion."""

    activity_confidence_min: float = Field(default=0.75, ge=0.0, le=1.0)
    pose_tracking_stability_min: float = Field(default=0.8, ge=0.0, le=1.0)
    interaction_proximity_px: float | None = None


class ValidationRule(BaseModel):
    """Perception invariant assertion evaluated on each frame."""

    rule_id: str
    predicate: str
    severity: Literal["INFO", "WARNING", "CRITICAL"] = "WARNING"


class ExperimentStep(BaseModel):
    """Individual procedural step within an experiment."""

    step_id: str
    step_number: int = Field(ge=1)
    description: str
    expected_activity: str
    expected_actions: list[str] = Field(default_factory=list)
    step_order: int | None = None
    optional: bool = False
    allowed_transitions: list[str] = Field(default_factory=list)
    retry_policy: dict[str, Any] = Field(default_factory=dict)
    preconditions: list[dict[str, Any]] = Field(default_factory=list)
    timeouts: StepTimeouts
    thresholds: StepThresholds
    validation_rules: list[ValidationRule] = Field(default_factory=list)

    @model_validator(mode="after")
    def _populate_step_defaults(self) -> "ExperimentStep":
        if not self.expected_actions and self.expected_activity:
            self.expected_actions = [self.expected_activity]
        if self.step_order is None:
            self.step_order = self.step_number
        return self


class ExperimentAlert(BaseModel):
    """Safety alert specification."""

    alert_id: str
    trigger: str
    severity: Literal["INFO", "WARNING", "CRITICAL", "EMERGENCY"]
    audio_chime: str | None = None
    spoken_message: str | None = None


class ExperimentRecovery(BaseModel):
    """Contingency recovery rules."""

    on_timeout: dict[str, Any] = Field(default_factory=dict)
    on_tool_lost: dict[str, Any] = Field(default_factory=dict)
    on_power_interrupt: dict[str, Any] = Field(default_factory=dict)


class ExperimentSpecification(BaseModel):
    """Master experiment specification matching experiment_template.yaml."""

    schema_version: str = "1.0.0"
    protocol_hash: str | None = None
    metadata: ExperimentMetadata
    objects: list[ExperimentObject]
    steps: list[ExperimentStep]
    alerts: list[ExperimentAlert] = Field(default_factory=list)
    recovery: ExperimentRecovery = Field(default_factory=ExperimentRecovery)
