"""Unit tests for ORION Protocol Engine components: Mapper, Decision Engine, FSM, Guidance."""

from datetime import datetime, timezone

import pytest
from experiments.loader import compute_protocol_hash, load_protocol, verify_protocol_integrity
from experiments.schemas import ExperimentSpecification

from orion.events.schemas import ActivityRecognized
from orion.protocol.action_mapping import ActivityToActionMapper
from orion.protocol.decision_engine import (
    DecisionStatus,
    ProtocolDecisionEngine,
)
from orion.protocol.next_step_engine import NextStepGuidanceEngine
from orion.protocol.state_machine import (
    ProtocolState,
    ProtocolStateError,
    ProtocolStateMachine,
)


@pytest.fixture
def canonical_spec() -> ExperimentSpecification:
    """Load canonical BAS protein crystal growth experiment specification."""
    return load_protocol("configs/protocols/bas_crystal_growth_v1.yaml")


def test_activity_to_action_mapper() -> None:
    """Verify mapping of raw HAR predictions and non-action status handling."""
    mapper = ActivityToActionMapper()

    # Canonical classes
    assert mapper.map_activity("prepare_workstation") == "prepare_workstation"
    assert mapper.map_activity("reach_tool") == "reach_tool"
    assert mapper.map_activity("grasp_tool") == "grasp_tool"
    assert mapper.map_activity("manipulate_sample") == "manipulate_sample"
    assert mapper.map_activity("inspect_chamber") == "inspect_chamber"
    assert mapper.map_activity("idle") == "idle"

    # Synonyms
    assert mapper.map_activity("prepare") == "prepare_workstation"
    assert mapper.map_activity("reach") == "reach_tool"
    assert mapper.map_activity("grasp") == "grasp_tool"

    # Non-action statuses must map to UNKNOWN
    assert mapper.map_activity("unknown") == "UNKNOWN"
    assert mapper.map_activity("uncertain") == "UNKNOWN"
    assert mapper.map_activity("warming_up") == "UNKNOWN"
    assert mapper.map_activity("degraded") == "UNKNOWN"
    assert mapper.map_activity("random_unseen_action") == "UNKNOWN"
    assert mapper.map_activity("") == "UNKNOWN"
    assert mapper.map_activity(None) == "UNKNOWN"


def test_protocol_loader_and_hashing(canonical_spec: ExperimentSpecification) -> None:
    """Verify cryptographic SHA-256 hash generation and integrity verification."""
    assert canonical_spec.protocol_hash is not None
    assert len(canonical_spec.protocol_hash) == 64
    assert len(canonical_spec.steps) == 6

    # Invariant hashing check
    computed = compute_protocol_hash(canonical_spec)
    assert computed == canonical_spec.protocol_hash
    assert verify_protocol_integrity(canonical_spec, computed)

    # Tamper check
    tampered_data = canonical_spec.model_dump()
    tampered_data["steps"][0]["timeouts"]["max_timeout_seconds"] = 999
    tampered_spec = ExperimentSpecification.model_validate(tampered_data)
    assert not verify_protocol_integrity(tampered_spec, canonical_spec.protocol_hash)


def test_decision_engine_entropy_and_uncertainty(canonical_spec: ExperimentSpecification) -> None:
    """Verify that high entropy and low confidence yield STEP_UNCERTAIN."""
    engine = ProtocolDecisionEngine(default_min_confidence=0.70, default_max_entropy=1.40)
    engine.reset_step()

    # High entropy event
    high_h_event = ActivityRecognized(
        track_id=1,
        window_start_frame=0,
        window_end_frame=32,
        activity_label="prepare_workstation",
        confidence=0.80,
        evidence_metadata={"entropy": 1.65},
    )
    d1 = engine.evaluate(high_h_event, canonical_spec, current_step_index=0)
    assert d1.status == DecisionStatus.STEP_UNCERTAIN

    # Low confidence event
    low_c_event = ActivityRecognized(
        track_id=1,
        window_start_frame=32,
        window_end_frame=64,
        activity_label="prepare_workstation",
        confidence=0.45,
        evidence_metadata={"entropy": 0.30},
    )
    d2 = engine.evaluate(low_c_event, canonical_spec, current_step_index=0)
    assert d2.status == DecisionStatus.STEP_UNCERTAIN

    # Unknown activity label
    unknown_event = ActivityRecognized(
        track_id=1,
        window_start_frame=64,
        window_end_frame=96,
        activity_label="unknown",
        confidence=0.90,
        evidence_metadata={"entropy": 0.20},
    )
    d3 = engine.evaluate(unknown_event, canonical_spec, current_step_index=0)
    assert d3.status == DecisionStatus.WAITING_FOR_EVIDENCE


def test_decision_engine_debouncing(canonical_spec: ExperimentSpecification) -> None:
    """Verify temporal debounce requires K=2 consecutive windows for VALID transition."""
    engine = ProtocolDecisionEngine(default_debounce_threshold=2)
    engine.reset_step()

    valid_event = ActivityRecognized(
        track_id=1,
        window_start_frame=0,
        window_end_frame=32,
        activity_label="prepare_workstation",
        confidence=0.90,
        evidence_metadata={"entropy": 0.30},
    )

    # Window 1: Debouncing (1/2) -> WAITING_FOR_EVIDENCE
    d1 = engine.evaluate(valid_event, canonical_spec, current_step_index=0)
    assert d1.status == DecisionStatus.WAITING_FOR_EVIDENCE
    assert d1.debounce_count == 1

    # Window 2: Debounced (2/2) -> VALID
    d2 = engine.evaluate(valid_event, canonical_spec, current_step_index=0)
    assert d2.status == DecisionStatus.VALID
    assert d2.debounce_count == 2


def _fsm_state(machine: ProtocolStateMachine) -> ProtocolState:
    return machine.state


def test_state_machine_full_lifecycle(canonical_spec: ExperimentSpecification) -> None:
    """Verify 11-state FSM lifecycle transitions and operator controls."""
    fsm = ProtocolStateMachine()
    assert _fsm_state(fsm) == ProtocolState.IDLE

    # Load protocol
    fsm.load_protocol(canonical_spec)
    assert _fsm_state(fsm) == ProtocolState.LOADED

    # Precheck
    fsm.start_precheck()
    assert _fsm_state(fsm) == ProtocolState.PRECHECK

    # Start run
    fsm.start_run("run_unit_001")
    assert _fsm_state(fsm) == ProtocolState.RUNNING
    assert fsm.current_step_index == 0

    # Pause and resume
    fsm.pause()
    assert _fsm_state(fsm) == ProtocolState.PAUSED
    fsm.resume()
    assert _fsm_state(fsm) == ProtocolState.RUNNING

    # Invalid transition check
    with pytest.raises(ProtocolStateError):
        fsm._transition_to(ProtocolState.IDLE)  # Cannot jump directly from RUNNING to IDLE

    # Advance through all 6 steps
    for expected_step in range(1, len(canonical_spec.steps)):
        advanced = fsm.advance_step()
        assert advanced is True
        assert fsm.state == ProtocolState.STEP_IN_PROGRESS
        assert fsm.current_step_index == expected_step

    # Final step completion
    advanced_last = fsm.advance_step()
    assert advanced_last is False
    assert fsm.state == ProtocolState.COMPLETED


def test_next_step_guidance_engine(canonical_spec: ExperimentSpecification) -> None:
    """Verify real-time copilot recommendation calculation."""
    fsm = ProtocolStateMachine()
    fsm.load_protocol(canonical_spec)
    fsm.start_run("run_guidance_001")

    guidance_engine = NextStepGuidanceEngine()
    rec = guidance_engine.compute_recommendation(fsm)

    assert rec is not None
    assert rec.step_number == 1
    assert rec.total_steps == 6
    assert rec.expected_activity == "prepare_workstation"
    assert rec.nominal_duration_seconds == 60
    assert rec.is_last_step is False
    assert len(rec.hazard_warnings) > 0
