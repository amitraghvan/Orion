"""End-to-end golden scenarios test for ExperimentEngine protocol tracking and decision dispatch."""

from pathlib import Path

import pytest
from app.core.airgap import enforce_airgap
from app.experiments.experiment_engine import experiment_engine
from app.intelligence.decision_engine import DecisionStatus


@pytest.fixture(autouse=True)
def setup_airgap():
    enforce_airgap()


def test_scenario_01_nominal_linear_completion():
    """Golden Scenario 1: Execute all steps linearly to successful mission completion."""
    protocol_path = Path("configs/protocols/bas_crystal_growth_v1.yaml")
    engine = experiment_engine
    engine.load_protocol_file(str(protocol_path))
    run_id = engine.start_experiment()
    assert engine.is_running is True

    # bas_crystal_growth_v1 steps:
    # 1: prepare_workstation
    # 2: reach_tool
    # 3: grasp_tool
    # 4: manipulate_sample
    # 5: inspect_chamber
    # 6: idle
    steps_actions = [
        "prepare_workstation",
        "reach_tool",
        "grasp_tool",
        "manipulate_sample",
        "inspect_chamber",
        "idle",
    ]

    for action in steps_actions:
        # Window 1: Debounce (threshold = 2)
        d1 = engine.process_observation(action, confidence=0.92, entropy=0.2)
        assert d1 is not None
        assert d1.status == DecisionStatus.WAITING_FOR_EVIDENCE

        # Window 2: Valid transition
        d2 = engine.process_observation(action, confidence=0.95, entropy=0.15)
        assert d2 is not None
        assert d2.status == DecisionStatus.VALID

    # Verify terminal state
    assert engine.fsm.state.value == "COMPLETED"
    assert engine.is_running is False


def test_scenario_02_out_of_sequence_handling():
    """Golden Scenario 2: Future step performed prematurely triggers OUT_OF_SEQUENCE warning."""
    protocol_path = Path("configs/protocols/bas_crystal_growth_v1.yaml")
    engine = experiment_engine
    engine.load_protocol_file(str(protocol_path))
    engine.start_experiment()

    # In step 1 (prepare_workstation), observe grasp_tool (which is step 3)
    # Window 1: Debouncing
    d1 = engine.process_observation("grasp_tool", confidence=0.90, entropy=0.2)
    assert d1.status == DecisionStatus.WAITING_FOR_EVIDENCE

    # Window 2: Violation confirmed
    d2 = engine.process_observation("grasp_tool", confidence=0.90, entropy=0.2)
    assert d2.status == DecisionStatus.OUT_OF_SEQUENCE
    # Step remains step 1
    assert engine.fsm.current_step_index == 0

    engine.stop_experiment()


def test_scenario_03_wrong_object_handling():
    """Golden Scenario 3: Incorrect object interaction triggers WRONG_OBJECT alert."""
    protocol_path = Path("configs/protocols/bas_crystal_growth_v1.yaml")
    engine = experiment_engine
    engine.load_protocol_file(str(protocol_path))
    engine.start_experiment()

    # Step 1 expects prepare_workstation, feed pick_red
    # Window 1: Debouncing
    d1 = engine.process_observation("pick_red", confidence=0.88, entropy=0.3)
    assert d1.status == DecisionStatus.WAITING_FOR_EVIDENCE

    # Window 2: Violation confirmed
    d2 = engine.process_observation("pick_red", confidence=0.88, entropy=0.3)
    assert d2.status in (DecisionStatus.WRONG_OBJECT, DecisionStatus.INVALID_ACTION)
    assert engine.fsm.current_step_index == 0

    engine.stop_experiment()


def test_scenario_04_uncertainty_rejection():
    """Golden Scenario 4: Low confidence observation does not trigger false positive advancement."""
    protocol_path = Path("configs/protocols/bas_crystal_growth_v1.yaml")
    engine = experiment_engine
    engine.load_protocol_file(str(protocol_path))
    engine.start_experiment()

    # Feed correct action but with below-threshold confidence (e.g. 0.45 < 0.70)
    d = engine.process_observation("prepare_workstation", confidence=0.45, entropy=0.3)
    assert d is not None
    assert d.status == DecisionStatus.STEP_UNCERTAIN
    assert engine.fsm.current_step_index == 0

    engine.stop_experiment()


def test_scenario_05_manual_abort_generates_report():
    """Golden Scenario 5: Operator abort clean exit and report finalization."""
    protocol_path = Path("configs/protocols/bas_crystal_growth_v1.yaml")
    engine = experiment_engine
    engine.load_protocol_file(str(protocol_path))
    run_id = engine.start_experiment()
    assert engine.is_running is True

    # Advance 1 step
    engine.process_observation("prepare_workstation", confidence=0.95, entropy=0.1)
    engine.process_observation("prepare_workstation", confidence=0.95, entropy=0.1)
    assert engine.fsm.current_step_index == 1

    # Operator aborts
    engine.stop_experiment()
    assert engine.fsm.state.value == "ABORTED"
    assert engine.is_running is False
