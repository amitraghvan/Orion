"""The 15 Golden Test Scenarios for ORION Protocol Engine and Scientific Guidance Layer."""

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from experiments.loader import load_protocol, verify_protocol_integrity
from experiments.schemas import ExperimentSpecification

from orion.events.schemas import ActivityRecognized
from orion.protocol.decision_engine import DecisionStatus, ProtocolDecisionEngine
from orion.protocol.service import ProtocolService
from orion.protocol.state_machine import ProtocolState


@pytest.fixture
def protocol_path() -> Path:
    return Path("configs/protocols/bas_crystal_growth_v1.yaml")


@pytest.fixture
def spec(protocol_path: Path) -> ExperimentSpecification:
    return load_protocol(protocol_path)


def _make_event(
    activity: str,
    confidence: float = 0.90,
    entropy: float = 0.25,
    track_id: int = 1,
    uncertainty_status: str = "NOMINAL",
) -> ActivityRecognized:
    return ActivityRecognized(
        track_id=track_id,
        window_start_frame=0,
        window_end_frame=32,
        activity_label=activity,
        confidence=confidence,
        uncertainty_status=uncertainty_status,
        evidence_metadata={
            "entropy": entropy,
            "probabilities": {activity: confidence},
        },
    )


# SC-01: Nominal Linear Execution
@pytest.mark.asyncio
async def test_sc01_nominal_linear_execution(protocol_path: Path) -> None:
    """Steps 1 to 6 executed linearly with debounce K=2; terminal state is COMPLETED."""
    service = ProtocolService()
    service.load_protocol_file(protocol_path)
    service.start_experiment("run_sc01")

    actions = [
        "prepare_workstation",
        "reach_tool",
        "grasp_tool",
        "manipulate_sample",
        "inspect_chamber",
        "idle",
    ]

    for act in actions:
        # Window 1: Debouncing
        d1 = await service.process_activity(_make_event(act))
        assert d1 is not None
        assert d1.status == DecisionStatus.WAITING_FOR_EVIDENCE

        # Window 2: Valid transition
        d2 = await service.process_activity(_make_event(act))
        assert d2 is not None
        assert d2.status == DecisionStatus.VALID

    assert service.state == ProtocolState.COMPLETED
    rec = service._last_recommendation
    assert rec is not None
    assert rec.is_last_step is True


# SC-02: Out-of-Order Step Attempt
@pytest.mark.asyncio
async def test_sc02_out_of_order_step_attempt(protocol_path: Path) -> None:
    """Step 1 valid, then premature Step 4 observed twice -> SKIPPED / BLOCKED."""
    service = ProtocolService()
    service.load_protocol_file(protocol_path)
    service.start_experiment("run_sc02")

    # Complete Step 1
    await service.process_activity(_make_event("prepare_workstation"))
    await service.process_activity(_make_event("prepare_workstation"))
    assert service.fsm.current_step_index == 1  # Now on Step 2 (reach_tool)

    # Premature manipulate_sample (Step 4) twice
    d1 = await service.process_activity(_make_event("manipulate_sample"))
    assert d1 is not None
    assert d1.status == DecisionStatus.WAITING_FOR_EVIDENCE

    d2 = await service.process_activity(_make_event("manipulate_sample"))
    assert d2 is not None
    assert d2.status == DecisionStatus.SKIPPED
    assert service.state == ProtocolState.BLOCKED


# SC-03: Skipped Step Detection
@pytest.mark.asyncio
async def test_sc03_skipped_step_detection(protocol_path: Path) -> None:
    """Step 1 -> Step 2 -> Step 4 (Step 3 grasp_tool omitted) retroactively identifies skipped step."""
    service = ProtocolService()
    service.load_protocol_file(protocol_path)
    service.start_experiment("run_sc03")

    # Step 1
    await service.process_activity(_make_event("prepare_workstation"))
    await service.process_activity(_make_event("prepare_workstation"))

    # Step 2
    await service.process_activity(_make_event("reach_tool"))
    await service.process_activity(_make_event("reach_tool"))
    assert service.fsm.current_step is not None
    assert service.fsm.current_step.step_id == "step_03_grasp_tool"

    # Step 4 directly
    await service.process_activity(_make_event("manipulate_sample"))
    d_skip = await service.process_activity(_make_event("manipulate_sample"))
    assert d_skip is not None
    assert d_skip.status == DecisionStatus.SKIPPED
    assert "step_03_grasp_tool" in d_skip.retroactive_skip_step_ids
    assert service.state == ProtocolState.BLOCKED


# SC-04: Transient Noise Suppression
@pytest.mark.asyncio
async def test_sc04_transient_noise_suppression(protocol_path: Path) -> None:
    """Single spurious frame between nominal observations does not falsely advance or fail."""
    service = ProtocolService()
    service.load_protocol_file(protocol_path)
    service.start_experiment("run_sc04")

    # 1 valid observation
    d1 = await service.process_activity(_make_event("prepare_workstation"))
    assert d1 is not None
    assert d1.status == DecisionStatus.WAITING_FOR_EVIDENCE
    assert d1.debounce_count == 1

    # 1 transient spurious observation of unexpected action
    d_noise = await service.process_activity(_make_event("grasp_tool"))
    assert d_noise is not None
    assert d_noise.status == DecisionStatus.WAITING_FOR_EVIDENCE
    assert service.state.value == ProtocolState.STEP_IN_PROGRESS.value  # Not blocked!

    # Return to expected action
    d2 = await service.process_activity(_make_event("prepare_workstation"))
    assert d2 is not None
    assert d2.status == DecisionStatus.WAITING_FOR_EVIDENCE
    assert d2.debounce_count == 1  # Streak reset safely by noise


# SC-05: High-Entropy Uncertainty
@pytest.mark.asyncio
async def test_sc05_high_entropy_uncertainty(protocol_path: Path) -> None:
    """High entropy prediction (H=1.82 > 1.40) yields STEP_UNCERTAIN without violation."""
    service = ProtocolService()
    service.load_protocol_file(protocol_path)
    service.start_experiment("run_sc05")

    d = await service.process_activity(_make_event("prepare_workstation", entropy=1.82))
    assert d is not None
    assert d.status == DecisionStatus.STEP_UNCERTAIN
    assert service.state != ProtocolState.BLOCKED


# SC-06: Low-Confidence Rejection
@pytest.mark.asyncio
async def test_sc06_low_confidence_rejection(protocol_path: Path) -> None:
    """Low confidence (0.45 < 0.70) yields STEP_UNCERTAIN and does not trigger step advance."""
    service = ProtocolService()
    service.load_protocol_file(protocol_path)
    service.start_experiment("run_sc06")

    d = await service.process_activity(_make_event("prepare_workstation", confidence=0.45))
    assert d is not None
    assert d.status == DecisionStatus.STEP_UNCERTAIN
    assert service.fsm.current_step_index == 0


# SC-07: Step Timeout Exceeded
@pytest.mark.asyncio
async def test_sc07_step_timeout_exceeded(protocol_path: Path) -> None:
    """Step duration exceeding max_timeout_seconds emits TIMEOUT and blocks FSM."""
    service = ProtocolService()
    service.load_protocol_file(protocol_path)
    service.start_experiment("run_sc07")

    # Advance time by 300 seconds (step 1 max timeout is 180s)
    future_time = datetime.now(UTC) + timedelta(seconds=300)
    d = await service.process_activity(_make_event("prepare_workstation"), now=future_time)
    assert d is not None
    assert d.status == DecisionStatus.TIMEOUT
    assert service.state == ProtocolState.BLOCKED


# SC-08: Operator Pause and Resume
def test_sc08_operator_pause_and_resume(spec: ExperimentSpecification) -> None:
    """Pause halts execution and freeze state; resume restores RUNNING."""
    service = ProtocolService()
    service.fsm.load_protocol(spec)
    service.start_experiment("run_sc08")

    service.pause("Crew drink break")
    assert service.state.value == ProtocolState.PAUSED.value

    service.resume("Crew back at glovebox")
    assert service.state.value == ProtocolState.RUNNING.value


# SC-09: Operator Abort Lifecycle
def test_sc09_operator_abort_lifecycle(spec: ExperimentSpecification) -> None:
    """Explicit abort command safely transitions state to ABORTED."""
    service = ProtocolService()
    service.fsm.load_protocol(spec)
    service.start_experiment("run_sc09")

    service.abort("Chamber seal leak detected")
    assert service.state.value == ProtocolState.ABORTED.value


# SC-10: Multi-Actor Tracking
@pytest.mark.asyncio
async def test_sc10_multi_actor_tracking(protocol_path: Path) -> None:
    """Secondary actor observations are ignored when primary actor is assigned."""
    service = ProtocolService()
    service.load_protocol_file(protocol_path)
    service.start_experiment("run_sc10", actor_track_id=1)

    # Observation from Track 2 (secondary crew member)
    d_track2 = await service.process_activity(_make_event("prepare_workstation", track_id=2))
    assert d_track2 is None  # Filtered out by actor tracking

    # Observation from Track 1 (primary crew member)
    d_track1 = await service.process_activity(_make_event("prepare_workstation", track_id=1))
    assert d_track1 is not None
    assert d_track1.debounce_count == 1


# SC-11: Retry Failed Step
@pytest.mark.asyncio
async def test_sc11_retry_failed_step(protocol_path: Path) -> None:
    """BLOCKED state resolved via RETRY returns to STEP_IN_PROGRESS and resets timer/debounce."""
    service = ProtocolService()
    service.load_protocol_file(protocol_path)
    service.start_experiment("run_sc11")

    # Cause timeout or skip deviation
    future = datetime.now(UTC) + timedelta(seconds=500)
    await service.process_activity(_make_event("idle"), now=future)
    assert service.state.value == ProtocolState.BLOCKED.value

    # Resolve via RETRY
    service.resolve_blocked("RETRY")
    assert service.state.value == ProtocolState.STEP_IN_PROGRESS.value
    assert service.decision_engine._action_streak_count == 0


# SC-12: Unknown Class Observation
@pytest.mark.asyncio
async def test_sc12_unknown_class_observation(protocol_path: Path) -> None:
    """Unmapped activity strings emit WAITING_FOR_EVIDENCE with 0 violations."""
    service = ProtocolService()
    service.load_protocol_file(protocol_path)
    service.start_experiment("run_sc12")

    d = await service.process_activity(_make_event("unmapped_astronaut_scratching_nose"))
    assert d is not None
    assert d.status == DecisionStatus.WAITING_FOR_EVIDENCE
    assert service.state != ProtocolState.BLOCKED


# SC-13: Rapid Succession Debounce
@pytest.mark.asyncio
async def test_sc13_rapid_succession_debounce(protocol_path: Path) -> None:
    """10 rapidly alternating actions do not trigger spurious state transitions."""
    service = ProtocolService()
    service.load_protocol_file(protocol_path)
    service.start_experiment("run_sc13")

    alternating = ["prepare_workstation", "reach_tool"] * 5
    for act in alternating:
        d = await service.process_activity(_make_event(act))
        assert d is not None
        assert d.status == DecisionStatus.WAITING_FOR_EVIDENCE

    # Step 1 should remain active, not transitioned
    assert service.fsm.current_step_index == 0


# SC-14: Protocol Hash Tamper Detection
def test_sc14_protocol_hash_tamper_detection(spec: ExperimentSpecification) -> None:
    """Tampering with protocol parameters is immediately caught by hash verification."""
    original_hash = spec.protocol_hash
    assert original_hash is not None

    # Verify original
    assert verify_protocol_integrity(spec, original_hash)

    # Modify a parameter
    modified_dict = spec.model_dump()
    modified_dict["steps"][0]["expected_activity"] = "hacked_activity"
    tampered_spec = ExperimentSpecification.model_validate(modified_dict)

    # Integrity verification must fail
    assert not verify_protocol_integrity(tampered_spec, original_hash)


# SC-15: Fault-Isolated Recovery
@pytest.mark.asyncio
async def test_sc15_fault_isolated_recovery(protocol_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Internal exception in evaluation drops FSM to DEGRADED without crashing."""
    service = ProtocolService()
    service.load_protocol_file(protocol_path)
    service.start_experiment("run_sc15")

    # Force an unexpected internal exception in decision engine
    def _faulty_evaluate(*args: object, **kwargs: object) -> None:
        raise RuntimeError("Simulated hardware perception / compute failure")

    monkeypatch.setattr(service.decision_engine, "evaluate", _faulty_evaluate)

    d = await service.process_activity(_make_event("prepare_workstation"))
    assert d is None
    assert service.state == ProtocolState.DEGRADED

