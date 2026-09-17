"""Unit tests for the 11-state ProtocolStateMachine."""

import pytest
from app.core.exceptions import ProtocolStateError
from app.experiments.experiment_schema import ExperimentMetadata, ExperimentSpecification, ExperimentStep
from app.experiments.sequence_manager import ProtocolState, ProtocolStateMachine


@pytest.fixture
def mock_specification() -> ExperimentSpecification:
    """Fixture providing a valid 2-step experiment specification."""
    return ExperimentSpecification(
        metadata=ExperimentMetadata(
            experiment_id="EXP-TEST-01",
            title="Test Experiment",
            version="1.0.0",
            category="Biological",
        ),
        steps=[
            ExperimentStep(
                step_number=1,
                step_id="S01",
                description="Pick pipette",
                action_class="pick_pipette",
                expected_objects=["pipette"],
                timeout_seconds=30.0,
            ),
            ExperimentStep(
                step_number=2,
                step_id="S02",
                description="Aspirate sample",
                action_class="aspirate",
                expected_objects=["pipette", "vial"],
                timeout_seconds=45.0,
            ),
        ],
    )


def test_initial_state():
    fsm = ProtocolStateMachine()
    assert fsm.state == ProtocolState.IDLE
    assert fsm.spec is None
    assert fsm.current_step_index == 0


def test_load_spec(mock_specification):
    fsm = ProtocolStateMachine()
    fsm.load_spec(mock_specification)
    assert fsm.state == ProtocolState.LOADED
    assert fsm.spec == mock_specification
    assert fsm.current_step is not None
    assert fsm.current_step.step_id == "S01"


def test_full_execution_lifecycle(mock_specification):
    fsm = ProtocolStateMachine()
    fsm.load_spec(mock_specification)

    # Start
    fsm.start_execution()
    assert fsm.state == ProtocolState.STEP_IN_PROGRESS
    assert fsm.current_step_index == 0

    # Advance Step 1 -> Step 2
    is_done = fsm.advance_step()
    assert is_done is False
    assert fsm.state == ProtocolState.STEP_IN_PROGRESS
    assert fsm.current_step_index == 1
    assert fsm.current_step.step_id == "S02"

    # Advance Step 2 -> Finished
    is_done = fsm.advance_step()
    assert is_done is True
    assert fsm.state == ProtocolState.COMPLETED


def test_pause_and_resume(mock_specification):
    fsm = ProtocolStateMachine()
    fsm.load_spec(mock_specification)
    fsm.start_execution()

    fsm.pause()
    assert fsm.state == ProtocolState.PAUSED

    fsm.resume()
    assert fsm.state == ProtocolState.STEP_IN_PROGRESS


def test_abort_and_reset(mock_specification):
    fsm = ProtocolStateMachine()
    fsm.load_spec(mock_specification)
    fsm.start_execution()

    fsm.abort(reason="Emergency stop")
    assert fsm.state == ProtocolState.ABORTED

    fsm.reset()
    assert fsm.state == ProtocolState.IDLE
    assert fsm.spec is None


def test_invalid_transitions():
    fsm = ProtocolStateMachine()
    # Cannot go directly from IDLE to RUNNING without spec
    with pytest.raises(ProtocolStateError):
        fsm.start_execution()

    # Cannot advance when IDLE
    assert fsm.advance_step() is False
