"""Declarative SQLite SQLAlchemy models for ORION mission records."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class ExperimentModel(Base):
    __tablename__ = "experiments"

    experiment_id = Column(String(64), primary_key=True)
    title = Column(String(255), nullable=False)
    lead_agency = Column(String(64), default="ISRO HSFC")
    station_module = Column(String(64), default="BAS-SCIENCE-NODE-1")
    glovebox_id = Column(String(32), default="GB-01")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    runs = relationship("ExperimentRunModel", back_populates="experiment")


class ExperimentRunModel(Base):
    __tablename__ = "experiment_runs"

    run_id = Column(String(64), primary_key=True)
    experiment_id = Column(String(64), ForeignKey("experiments.experiment_id"), nullable=False)
    status = Column(String(32), default="RUNNING")
    start_time = Column(DateTime, default=lambda: datetime.now(UTC))
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0.0)
    total_steps = Column(Integer, default=0)
    completed_steps = Column(Integer, default=0)
    skipped_steps = Column(Integer, default=0)
    violations_count = Column(Integer, default=0)

    experiment = relationship("ExperimentModel", back_populates="runs")
    steps = relationship("ExperimentStepLogModel", back_populates="run")


class ExperimentStepLogModel(Base):
    __tablename__ = "experiment_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("experiment_runs.run_id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    step_id = Column(String(64), nullable=False)
    expected_action = Column(String(64), nullable=False)
    detected_action = Column(String(64), nullable=False)
    status = Column(String(32), default="VALID")
    confidence = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))
    explanation = Column(Text, default="")

    run = relationship("ExperimentRunModel", back_populates="steps")


class AlertModel(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=True)
    severity = Column(String(16), default="INFO")
    message = Column(Text, nullable=False)
    source = Column(String(64), default="COPILOT")
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))
    acknowledged = Column(Boolean, default=False)


class SystemEventModel(Base):
    __tablename__ = "system_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(64), nullable=False)
    details = Column(Text, default="")
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))
