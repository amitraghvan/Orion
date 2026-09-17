"""Next-step scientific guidance and astronaut copilot recommendation engine."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from orion.protocol.state_machine import ProtocolState, ProtocolStateMachine


class NextStepRecommendation(BaseModel):
    """Real-time astronaut procedural guidance and timing recommendations."""

    step_id: str
    step_number: int
    total_steps: int
    expected_activity: str
    expected_actions: list[str] = Field(default_factory=list)
    instruction_text: str
    nominal_duration_seconds: int
    max_timeout_seconds: int
    elapsed_seconds: float = 0.0
    remaining_nominal_seconds: float = 0.0
    hazard_warnings: list[str] = Field(default_factory=list)
    is_last_step: bool = False
    fsm_state: str = "RUNNING"


class NextStepGuidanceEngine:
    """Computes contextual next-step instructions, countdowns, and safety notes."""

    def compute_recommendation(
        self,
        fsm: ProtocolStateMachine,
        now: datetime | None = None,
    ) -> NextStepRecommendation | None:
        """Derive actionable procedural guidance from current FSM and protocol state."""
        spec = fsm.spec
        if not spec or not spec.steps:
            return None

        current_idx = fsm.current_step_index
        total_steps = len(spec.steps)

        if current_idx >= total_steps or fsm.state == ProtocolState.COMPLETED:
            return NextStepRecommendation(
                step_id="COMPLETED",
                step_number=total_steps,
                total_steps=total_steps,
                expected_activity="idle",
                expected_actions=["idle"],
                instruction_text="Experiment complete. Verify all samples sealed and workstation powered down.",
                nominal_duration_seconds=0,
                max_timeout_seconds=0,
                elapsed_seconds=0.0,
                remaining_nominal_seconds=0.0,
                hazard_warnings=[],
                is_last_step=True,
                fsm_state=fsm.state.value,
            )

        step = spec.steps[current_idx]
        current_now = now or datetime.now(UTC)

        elapsed = 0.0
        if fsm._step_start_time:
            elapsed = max(0.0, (current_now - fsm._step_start_time).total_seconds())

        remaining_nom = max(0.0, step.timeouts.nominal_duration_seconds - elapsed)

        # Collect applicable hazard warnings
        hazards: list[str] = []
        for alert in spec.alerts:
            if alert.severity in ("WARNING", "CRITICAL", "EMERGENCY"):
                hazards.append(f"[{alert.severity}] {alert.spoken_message or alert.alert_id}")

        is_last = current_idx == total_steps - 1

        return NextStepRecommendation(
            step_id=step.step_id,
            step_number=step.step_number,
            total_steps=total_steps,
            expected_activity=step.expected_activity,
            expected_actions=step.expected_actions,
            instruction_text=step.description,
            nominal_duration_seconds=step.timeouts.nominal_duration_seconds,
            max_timeout_seconds=step.timeouts.max_timeout_seconds,
            elapsed_seconds=round(elapsed, 1),
            remaining_nominal_seconds=round(remaining_nom, 1),
            hazard_warnings=hazards,
            is_last_step=is_last,
            fsm_state=fsm.state.value,
        )
