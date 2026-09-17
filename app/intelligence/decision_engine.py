"""Confidence-calibrated protocol decision engine enforcing safety invariants and debouncing."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from app.core.logging import get_logger
from pydantic import BaseModel, Field

logger = get_logger("app.intelligence.decision")

MIN_PROBABILITY_EPSILON = 1e-9


class DecisionStatus(StrEnum):
    """Sequence validation and decision status."""

    VALID = "VALID"
    INVALID_ACTION = "INVALID_ACTION"
    WRONG_OBJECT = "WRONG_OBJECT"
    OUT_OF_SEQUENCE = "OUT_OF_SEQUENCE"
    SKIPPED = "SKIPPED"
    INTERRUPTED = "INTERRUPTED"
    STEP_UNCERTAIN = "STEP_UNCERTAIN"
    WAITING_FOR_EVIDENCE = "WAITING_FOR_EVIDENCE"
    TIMEOUT = "TIMEOUT"
    COMPLETED = "COMPLETED"


class ProtocolDecision(BaseModel):
    """Immutable record of an evaluated protocol decision with linked evidence."""

    decision_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: DecisionStatus
    step_id: str
    step_number: int
    observed_action: str
    expected_actions: list[str]
    confidence: float
    entropy: float
    debounce_count: int
    debounce_threshold: int
    explanation: str
    retroactive_skip_step_ids: list[str] = Field(default_factory=list)


class ActionMapper:
    """Normalizes raw model class strings to canonical protocol action tokens."""

    SYNONYMS = {
        "pick_yellow": "pick_yellow",
        "place_yellow": "place_yellow",
        "pick_red": "pick_red",
        "place_red": "place_red",
        "move_box": "move_box",
        "check_box": "inspect_box",
        "overlap_boxes": "overlap_boxes",
        "prepare_workstation": "prepare_workstation",
        "reach_tool": "reach_tool",
        "grasp_tool": "grasp_tool",
        "manipulate_sample": "manipulate_sample",
        "inspect_chamber": "inspect_chamber",
        "idle": "idle",
    }

    def map_action(self, raw_activity: str) -> str:
        clean = raw_activity.strip().lower()
        return self.SYNONYMS.get(clean, clean)


class ProtocolDecisionEngine:
    """Evaluates activity observations against active protocol specifications."""

    def __init__(
        self,
        default_min_confidence: float = 0.65,
        default_max_entropy: float = 1.40,
        default_debounce_threshold: int = 2,
    ) -> None:
        self.default_min_confidence = default_min_confidence
        self.default_max_entropy = default_max_entropy
        self.default_debounce_threshold = default_debounce_threshold
        self.mapper = ActionMapper()

        self._last_observed_action: str | None = None
        self._action_streak_count: int = 0
        self._step_start_time: datetime | None = None

    def reset_step(self, start_time: datetime | None = None) -> None:
        """Reset internal debounce streak and timer for step."""
        self._last_observed_action = None
        self._action_streak_count = 0
        self._step_start_time = start_time or datetime.now(UTC)

    def evaluate(
        self,
        observed_activity: str,
        confidence: float,
        entropy: float,
        spec: Any,
        current_step_index: int,
        now: datetime | None = None,
    ) -> ProtocolDecision:
        """Evaluate observation against active step."""
        current_now = now or datetime.now(UTC)
        if self._step_start_time is None:
            self._step_start_time = current_now

        if spec is None or not hasattr(spec, "steps") or current_step_index >= len(spec.steps):
            return ProtocolDecision(
                status=DecisionStatus.COMPLETED,
                step_id="FINISHED",
                step_number=len(spec.steps) if spec and hasattr(spec, "steps") else 0,
                observed_action="idle",
                expected_actions=[],
                confidence=confidence,
                entropy=entropy,
                debounce_count=0,
                debounce_threshold=self.default_debounce_threshold,
                explanation="All protocol steps completed.",
            )

        current_step = spec.steps[current_step_index]
        expected_actions = [a.lower() for a in getattr(current_step, "expected_actions", [])]
        step_id = getattr(current_step, "step_id", f"step_{current_step_index + 1}")
        step_num = getattr(current_step, "step_number", current_step_index + 1)
        mapped_action = self.mapper.map_action(observed_activity).lower()

        # Update debounce streak
        if mapped_action == self._last_observed_action:
            self._action_streak_count += 1
        else:
            self._last_observed_action = mapped_action
            self._action_streak_count = 1

        # 1. Check for idle when idle is NOT the expected action: nominal waiting
        if mapped_action == "idle" and "idle" not in expected_actions:
            return ProtocolDecision(
                status=DecisionStatus.WAITING_FOR_EVIDENCE,
                step_id=step_id,
                step_number=step_num,
                observed_action=mapped_action,
                expected_actions=expected_actions,
                confidence=confidence,
                entropy=entropy,
                debounce_count=self._action_streak_count,
                debounce_threshold=self.default_debounce_threshold,
                explanation="Astronaut is idle; awaiting procedural action.",
            )

        # 2. Check confidence & entropy invariants
        min_conf = getattr(
            getattr(current_step, "thresholds", None),
            "activity_confidence_min",
            self.default_min_confidence,
        )
        if confidence < min_conf or entropy > self.default_max_entropy:
            return ProtocolDecision(
                status=DecisionStatus.STEP_UNCERTAIN,
                step_id=step_id,
                step_number=step_num,
                observed_action=mapped_action,
                expected_actions=expected_actions,
                confidence=confidence,
                entropy=entropy,
                debounce_count=self._action_streak_count,
                debounce_threshold=self.default_debounce_threshold,
                explanation=f"AI observation is uncertain (conf={confidence:.2f}, entropy={entropy:.2f}). Continuing observation.",
            )

        # 3. Check debouncing threshold
        if self._action_streak_count < self.default_debounce_threshold:
            return ProtocolDecision(
                status=DecisionStatus.WAITING_FOR_EVIDENCE,
                step_id=step_id,
                step_number=step_num,
                observed_action=mapped_action,
                expected_actions=expected_actions,
                confidence=confidence,
                entropy=entropy,
                debounce_count=self._action_streak_count,
                debounce_threshold=self.default_debounce_threshold,
                explanation=f"Awaiting temporal confirmation for action '{mapped_action}' (streak {self._action_streak_count}/{self.default_debounce_threshold}).",
            )

        # 4. Check if observed action satisfies current step
        if any(
            mapped_action == exp or mapped_action in exp or exp in mapped_action
            for exp in expected_actions
        ):
            return ProtocolDecision(
                status=DecisionStatus.VALID,
                step_id=step_id,
                step_number=step_num,
                observed_action=mapped_action,
                expected_actions=expected_actions,
                confidence=confidence,
                entropy=entropy,
                debounce_count=self._action_streak_count,
                debounce_threshold=self.default_debounce_threshold,
                explanation=f"Step {step_num} successfully verified: '{mapped_action}'.",
            )

        # 5. Check if action corresponds to wrong object
        if ("yellow" in mapped_action and any("red" in exp for exp in expected_actions)) or (
            "red" in mapped_action and any("yellow" in exp for exp in expected_actions)
        ):
            return ProtocolDecision(
                status=DecisionStatus.WRONG_OBJECT,
                step_id=step_id,
                step_number=step_num,
                observed_action=mapped_action,
                expected_actions=expected_actions,
                confidence=confidence,
                entropy=entropy,
                debounce_count=self._action_streak_count,
                debounce_threshold=self.default_debounce_threshold,
                explanation=f"Wrong object manipulated! Observed '{mapped_action}', expected {expected_actions}.",
            )

        # 6. Check if action matches a future step (Out of sequence / Skipped step)
        for future_idx in range(current_step_index + 1, len(spec.steps)):
            future_step = spec.steps[future_idx]
            future_actions = [a.lower() for a in getattr(future_step, "expected_actions", [])]
            if any(mapped_action == f_act or mapped_action in f_act for f_act in future_actions):
                skipped_ids = [s.step_id for s in spec.steps[current_step_index:future_idx]]
                return ProtocolDecision(
                    status=DecisionStatus.OUT_OF_SEQUENCE,
                    step_id=step_id,
                    step_number=step_num,
                    observed_action=mapped_action,
                    expected_actions=expected_actions,
                    confidence=confidence,
                    entropy=entropy,
                    debounce_count=self._action_streak_count,
                    debounce_threshold=self.default_debounce_threshold,
                    explanation=f"Out-of-sequence activity detected! Observed action '{mapped_action}' belongs to Step {future_step.step_number}.",
                    retroactive_skip_step_ids=skipped_ids,
                )

        # 7. Unrecognized or unexpected action
        return ProtocolDecision(
            status=DecisionStatus.INVALID_ACTION,
            step_id=step_id,
            step_number=step_num,
            observed_action=mapped_action,
            expected_actions=expected_actions,
            confidence=confidence,
            entropy=entropy,
            debounce_count=self._action_streak_count,
            debounce_threshold=self.default_debounce_threshold,
            explanation=f"Unexpected activity '{mapped_action}' executed during step {step_num}.",
        )
