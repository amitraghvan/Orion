"""Contract test verifying experiment_template.yaml validates against ExperimentSpecification schema."""

from pathlib import Path

import pytest
import yaml
from experiments.schemas import ExperimentSpecification


@pytest.mark.contract
def test_experiment_template_yaml_validates() -> None:
    """Verify production experiment template matches Pydantic schema."""
    template_path = Path(__file__).resolve().parents[2] / "experiments" / "experiment_template.yaml"
    assert template_path.is_file(), f"Template not found at {template_path}"

    with open(template_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    spec = ExperimentSpecification.model_validate(data)
    assert spec.schema_version == "1.0.0"
    assert spec.metadata.experiment_id == "BAS-EXP-CRYSTAL-001"
    assert len(spec.objects) == 3
    assert len(spec.steps) == 3
    assert len(spec.alerts) == 2
