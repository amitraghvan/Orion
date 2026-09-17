"""Pydantic v2 schemas for parsing and validating BAS experiment specifications."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ExperimentMetadata(BaseModel):
    """Scientific experiment metadata and lead investigator information."""

    experiment_id: str
    title: str
    principal_investigator: str = "ISRO HSFC Payload Specialist"
    lead_agency: str = "ISRO HSFC"
    station_module: str = "BAS-SCIENCE-NODE-1"
    glovebox_id: str = "GB-01"
    revision: str = "1.0"
    date_approved: str = "2026-09-14"
    safety_classification: str = "LEVEL-1-NON-HAZARDOUS"


class ExperimentObject(BaseModel):
    """Target object, tool, or sample required by the experiment."""

    object_id: str
    label: str
    required: bool = True
    expected_detection_model: str = "yolo11n"
    min_confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class StepTimeouts(BaseModel):
    """Nominal and max allowed durations in seconds."""

    nominal_duration_seconds: int = Field(default=30, ge=1)
    max_timeout_seconds: int = Field(default=90, ge=1)


class StepThresholds(BaseModel):
    """Perception thresholds required to satisfy step completion."""

    activity_confidence_min: float = Field(default=0.65, ge=0.0, le=1.0)
    pose_tracking_stability_min: float = Field(default=0.75, ge=0.0, le=1.0)
    interaction_proximity_px: float | None = 120.0


class ValidationRule(BaseModel):
    """Rule evaluated against active perception."""

    rule_id: str
    predicate: str
    severity: Literal["INFO", "WARNING", "CRITICAL"] = "WARNING"


class ExperimentStep(BaseModel):
    """Individual procedural step within an experiment."""

    step_id: str
    step_number: int = Field(ge=1)
    description: str
    expected_activity: str | None = None
    expected_actions: list[str] = Field(default_factory=list)
    optional: bool = False
    allowed_transitions: list[str] = Field(default_factory=list)
    timeouts: StepTimeouts = Field(default_factory=StepTimeouts)
    thresholds: StepThresholds = Field(default_factory=StepThresholds)
    validation_rules: list[ValidationRule] = Field(default_factory=list)


class ExperimentSpecification(BaseModel):
    """Canonical BAS experiment protocol specification."""

    schema_version: str = "1.0.0"
    metadata: ExperimentMetadata
    objects: list[ExperimentObject] = Field(default_factory=list)
    steps: list[ExperimentStep] = Field(default_factory=list)
    protocol_hash: str | None = None
