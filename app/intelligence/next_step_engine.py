"""Next-step procedural guidance and recommendation engine for BAS experiments."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NextStepRecommendation(BaseModel):
    """Real-time astronaut procedural guidance."""

    current_step_number: int
    current_step_name: str
    next_step_number: int
    next_step_name: str
    expected_action: str
    required_objects: list[str] = Field(default_factory=list)
    instruction_text: str
    nominal_duration_seconds: int = 30
    is_completed: bool = False
    hazard_warnings: list[str] = Field(default_factory=list)


class NextStepEngine:
    """Computes actionable next-step instructions from protocol specification and active step pointer."""

    def compute_guidance(self, spec: Any, current_step_index: int) -> NextStepRecommendation:
        if spec is None or not hasattr(spec, "steps") or not spec.steps:
            return NextStepRecommendation(
                current_step_number=0,
                current_step_name="NO PROTOCOL LOADED",
                next_step_number=0,
                next_step_name="Awaiting protocol selection",
                expected_action="idle",
                instruction_text="Select and load a valid BAS experiment protocol to commence guidance.",
            )

        total_steps = len(spec.steps)

        if current_step_index >= total_steps:
            return NextStepRecommendation(
                current_step_number=total_steps,
                current_step_name="EXPERIMENT COMPLETED",
                next_step_number=total_steps,
                next_step_name="Experiment Completed",
                expected_action="idle",
                instruction_text="Experiment complete. Verify all samples sealed, containers stowed, and glovebox secure.",
                is_completed=True,
            )

        curr = spec.steps[current_step_index]
        curr_num = getattr(curr, "step_number", current_step_index + 1)
        curr_desc = getattr(curr, "description", getattr(curr, "step_id", f"Step {curr_num}"))

        if current_step_index + 1 < total_steps:
            nxt = spec.steps[current_step_index + 1]
            nxt_num = getattr(nxt, "step_number", current_step_index + 2)
            nxt_desc = getattr(nxt, "description", getattr(nxt, "step_id", f"Step {nxt_num}"))
            nxt_exp_actions = getattr(nxt, "expected_actions", ["execute"])
            exp_action_str = nxt_exp_actions[0].replace("_", " ") if nxt_exp_actions else "execute"
            instruction = f"Prepare for Step {nxt_num}: {nxt_desc}"
        else:
            nxt_num = curr_num
            nxt_desc = "Final Step (Finalize Experiment)"
            exp_action_str = "seal and stow"
            instruction = "Final step in progress. Conclude sampling and prepare glovebox stowage."

        # Collect required objects
        req_objs = []
        if hasattr(spec, "objects"):
            req_objs = [
                getattr(o, "label", getattr(o, "object_id", "item"))
                for o in spec.objects
                if getattr(o, "required", False)
            ]

        duration = 30
        if hasattr(curr, "timeouts") and hasattr(curr.timeouts, "nominal_duration_seconds"):
            duration = curr.timeouts.nominal_duration_seconds

        return NextStepRecommendation(
            current_step_number=curr_num,
            current_step_name=curr_desc,
            next_step_number=nxt_num,
            next_step_name=nxt_desc,
            expected_action=exp_action_str,
            required_objects=req_objs,
            instruction_text=instruction,
            nominal_duration_seconds=duration,
        )
