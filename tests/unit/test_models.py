"""Unit tests verifying SQLAlchemy ORM declarative model definitions."""

import pytest

from orion.db.models import (
    Alert,
    DatasetVersion,
    Event,
    Experiment,
    ModelVersion,
    Recording,
    Run,
    Step,
    SystemHealth,
)


@pytest.mark.unit
def test_orm_models_declared() -> None:
    """Verify all 9 core entities are correctly registered."""
    models = [
        Alert,
        DatasetVersion,
        Event,
        Experiment,
        ModelVersion,
        Recording,
        Run,
        Step,
        SystemHealth,
    ]
    for model in models:
        assert hasattr(model, "__tablename__")
        assert hasattr(model, "id")
        assert hasattr(model, "created_at")
        assert hasattr(model, "updated_at")
