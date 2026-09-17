"""Unit tests for ProtocolDecisionEngine."""

import pytest
from app.experiments.experiment_schema import ExperimentMetadata, ExperimentSpecification, ExperimentStep
from app.intelligence.decision_engine import DecisionStatus, ProtocolDecisionEngine


@pytest.fixture
def mock_spec():
    return ExperimentSpecification(
        metadata=ExperimentMetadata(
            experiment_id="EXP-E01-A",
            title="Sample Transfer Protocol",
            version="1.0",
            category="Physical",
        ),
        steps=[
            ExperimentStep(
                step_number=1,
                step_id="S01",
                description="Pick yellow box",
                expected_actions=["pick_yellow"],
                action_class="pick_yellow",
            ),
            ExperimentStep(
                step_number=2,
                step_id="S02",
                description="Place yellow box",
                expected_actions=["place_yellow"],
                action_class="place_yellow",
            ),
        ],
    )


def test_debounce_and_valid_action(mock_spec):
    engine = ProtocolDecisionEngine(default_debounce_threshold=2, default_min_confidence=0.7)
    engine.reset_step()

    # First observation: debounce count = 1 -> WAITING_FOR_EVIDENCE
    d1 = engine.evaluate("pick_yellow", confidence=0.85, entropy=0.4, spec=mock_spec, current_step_index=0)
    assert d1.status == DecisionStatus.WAITING_FOR_EVIDENCE
    assert d1.debounce_count == 1

    # Second observation: debounce count = 2 -> VALID
    d2 = engine.evaluate("pick_yellow", confidence=0.88, entropy=0.3, spec=mock_spec, current_step_index=0)
    assert d2.status == DecisionStatus.VALID
    assert d2.debounce_count == 2


def test_uncertain_confidence_and_entropy(mock_spec):
    engine = ProtocolDecisionEngine(default_debounce_threshold=1, default_min_confidence=0.7, default_max_entropy=1.4)
    engine.reset_step()

    # Low confidence
    d_low_conf = engine.evaluate("pick_yellow", confidence=0.5, entropy=0.4, spec=mock_spec, current_step_index=0)
    assert d_low_conf.status == DecisionStatus.STEP_UNCERTAIN

    # High entropy
    d_high_ent = engine.evaluate("pick_yellow", confidence=0.9, entropy=2.1, spec=mock_spec, current_step_index=0)
    assert d_high_ent.status == DecisionStatus.STEP_UNCERTAIN


def test_wrong_object_detection(mock_spec):
    engine = ProtocolDecisionEngine(default_debounce_threshold=1)
    engine.reset_step()

    # Observed red box instead of yellow
    d = engine.evaluate("pick_red", confidence=0.85, entropy=0.4, spec=mock_spec, current_step_index=0)
    assert d.status == DecisionStatus.WRONG_OBJECT


def test_out_of_sequence_detection(mock_spec):
    engine = ProtocolDecisionEngine(default_debounce_threshold=1)
    engine.reset_step()

    # In Step 0 (expected pick_yellow), observe place_yellow (which belongs to Step 1)
    d = engine.evaluate("place_yellow", confidence=0.9, entropy=0.3, spec=mock_spec, current_step_index=0)
    assert d.status == DecisionStatus.OUT_OF_SEQUENCE
    assert "S01" in d.retroactive_skip_step_ids


def test_invalid_action(mock_spec):
    engine = ProtocolDecisionEngine(default_debounce_threshold=1)
    engine.reset_step()

    d = engine.evaluate("drink_water", confidence=0.85, entropy=0.4, spec=mock_spec, current_step_index=0)
    assert d.status == DecisionStatus.INVALID_ACTION


def test_completed_state(mock_spec):
    engine = ProtocolDecisionEngine()
    d = engine.evaluate("idle", confidence=0.9, entropy=0.2, spec=mock_spec, current_step_index=2)
    assert d.status == DecisionStatus.COMPLETED
