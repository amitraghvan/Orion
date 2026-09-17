"""Unit tests for BAS experiments protocol validation and violation detection."""

from datetime import UTC, datetime

import pytest
from experiments.loader import load_protocol

from orion.events.schemas import ActivityRecognized
from orion.protocol.action_mapping import ActivityToActionMapper
from orion.protocol.decision_engine import DecisionStatus, ProtocolDecisionEngine
from orion.protocol.service import ProtocolService
from orion.protocol.state_machine import ProtocolState


def test_load_all_bas_protocols():
    """Verify that all 10 BAS protocols load cleanly with valid steps."""
    for exp in ["e01", "e02", "e03", "e04", "e05"]:
        for var in ["a", "b"]:
            spec = load_protocol(f"configs/protocols/bas_{exp}_{var}.yaml")
            assert spec.metadata.experiment_id.startswith("BAS-EXP")
            assert len(spec.steps) >= 2


def test_wrong_object_violation_detection():
    """Verify that manipulating a red box when yellow is expected flags WRONG_OBJECT."""
    spec = load_protocol("configs/protocols/bas_e01_a.yaml")
    engine = ProtocolDecisionEngine()
    engine.reset_step()

    # Step 1 expects pick_yellow
    event_red = ActivityRecognized(
        station_id="BAS-TEST",
        track_id=1,
        frame_index=10,
        window_start_frame=0,
        window_end_frame=10,
        activity_label="pick_red",
        confidence=0.92,
        model_version="BAS-HAR-v1.0",
    )

    # 1st observation: debounce streak 1 -> WAITING_FOR_EVIDENCE
    dec1 = engine.evaluate(event_red, spec, current_step_index=0)
    assert dec1.status == DecisionStatus.WAITING_FOR_EVIDENCE

    # 2nd observation: debounced streak 2 -> WRONG_OBJECT
    dec2 = engine.evaluate(event_red, spec, current_step_index=0)
    assert dec2.status == DecisionStatus.WRONG_OBJECT
    assert "Wrong object" in dec2.explanation


def test_valid_step_execution_and_next_step():
    """Verify that expected action advances step and produces next step recommendation."""
    service = ProtocolService()
    spec = service.load_protocol_file("configs/protocols/bas_e01_a.yaml")
    run_id = service.start_experiment()
    assert service.state == ProtocolState.RUNNING

    # Step 1: pick_yellow
    event_yellow = ActivityRecognized(
        station_id="BAS-TEST",
        track_id=1,
        frame_index=10,
        window_start_frame=0,
        window_end_frame=10,
        activity_label="pick_yellow",
        confidence=0.95,
        model_version="BAS-HAR-v1.0",
    )

    import asyncio

    # Send twice to satisfy debounce threshold
    asyncio.run(service.process_activity(event_yellow))
    dec = asyncio.run(service.process_activity(event_yellow))

    assert dec is not None
    assert dec.status == DecisionStatus.VALID
    rec = service.current_recommendation
    assert rec is not None
    assert rec.step_number == 2
    assert "place_yellow" in rec.expected_activity
