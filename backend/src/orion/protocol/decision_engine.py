"""Confidence-calibrated protocol decision engine enforcing safety invariants and debouncing."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from orion.protocol.action_mapping import ActivityToActionMapper
from orion.protocol.evidence import ProtocolEvidence

if TYPE_CHECKING:
    from experiments.schemas import ExperimentSpecification, ExperimentStep

    from orion.events.schemas import ActivityRecognized

MIN_PROBABILITY_EPSILON = 1e-9


class DecisionStatus(StrEnum):
    """Evaluation status yielded by the ProtocolDecisionEngine."""

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
    evidence: ProtocolEvidence
    retroactive_skip_step_ids: list[str] = Field(default_factory=list)


class ProtocolDecisionEngine:
    """Evaluates activity recognition observations against protocol specifications.

    Enforces:
    1. Confidence thresholds (c >= min_confidence, default 0.70)
    2. Entropy calibration (H <= max_entropy, default 1.40)
    3. Temporal debouncing (K consecutive windows, default K=2)
    4. Safety Invariants:
       - UNKNOWN != WRONG (emits WAITING_FOR_EVIDENCE)
       - UNCERTAIN != VIOLATION (emits STEP_UNCERTAIN)
       - NOT DETECTED != SKIPPED (only debounced future action triggers SKIPPED)
    """

    def __init__(
        self,
        default_min_confidence: float = 0.70,
        default_max_entropy: float = 1.40,
        default_debounce_threshold: int = 2,
        action_mapper: ActivityToActionMapper | None = None,
    ) -> None:
        self._default_min_confidence = default_min_confidence
        self._default_max_entropy = default_max_entropy
        self._default_debounce_threshold = default_debounce_threshold
        self._mapper = action_mapper or ActivityToActionMapper()

        # Streak tracking for debouncing: action -> count
        self._last_observed_action: str | None = None
        self._action_streak_count: int = 0
        self._step_start_time: datetime | None = None

    def reset_step(self, start_time: datetime | None = None) -> None:
        """Reset internal debouncing streak and start timer for a new step."""
        self._last_observed_action = None
        self._action_streak_count = 0
        self._step_start_time = start_time or datetime.now(UTC)

    @staticmethod
    def calculate_entropy(probabilities: dict[str, float]) -> float:
        """Compute Shannon entropy H(p) = -sum(p * ln(p)) over class distribution."""
        if not probabilities:
            return 0.0
        entropy = 0.0
        for p in probabilities.values():
            if p > MIN_PROBABILITY_EPSILON:
                entropy -= p * math.log(p)
        return float(entropy)

    def evaluate_step_timeout(
        self,
        current_step: ExperimentStep,
        now: datetime | None = None,
    ) -> bool:
        """Check whether the active step has exceeded its maximum timeout."""
        if not self._step_start_time:
            return False
        current_now = now or datetime.now(UTC)
        elapsed_s = (current_now - self._step_start_time).total_seconds()
        return elapsed_s > current_step.timeouts.max_timeout_seconds

    def evaluate(
        self,
        event: ActivityRecognized,
        spec: ExperimentSpecification,
        current_step_index: int,
        now: datetime | None = None,
    ) -> ProtocolDecision:
        """Evaluate an ActivityRecognized event against the current protocol step.

        Parameters:
            event: The incoming HAR activity event.
            spec: The loaded ExperimentSpecification.
            current_step_index: 0-based index of the currently active step.
            now: Optional current timestamp (for deterministic replay/testing).
        """
        current_now = now or datetime.now(UTC)
        if self._step_start_time is None:
            self._step_start_time = current_now

        if current_step_index >= len(spec.steps):
            evidence = ProtocolEvidence.from_activity_event(event, "idle", 0.0)
            return ProtocolDecision(
                status=DecisionStatus.COMPLETED,
                step_id="FINISHED",
                step_number=len(spec.steps),
                observed_action="idle",
                expected_actions=[],
                confidence=float(event.confidence),
                entropy=0.0,
                debounce_count=0,
                debounce_threshold=self._default_debounce_threshold,
                explanation="All protocol steps already completed successfully.",
                evidence=evidence,
            )

        current_step = spec.steps[current_step_index]
        expected_actions = [a.lower() for a in current_step.expected_actions]
        min_conf = (
            current_step.thresholds.activity_confidence_min
            if current_step.thresholds
            else self._default_min_confidence
        )

        # 1. Map raw activity string to canonical protocol action
        raw_label = event.activity_label
        mapped_action = self._mapper.map_activity(raw_label).lower()

        # Extract or compute entropy
        metadata = event.evidence_metadata or {}
        probs = metadata.get("probabilities", {})
        if "entropy" in metadata:
            entropy = float(metadata["entropy"])
        elif probs:
            entropy = self.calculate_entropy(probs)
        else:
            entropy = 0.0

        evidence = ProtocolEvidence.from_activity_event(event, mapped_action, entropy)

        # 2. Check for step timeout first
        if self.evaluate_step_timeout(current_step, current_now):
            elapsed_s = (current_now - self._step_start_time).total_seconds()
            return ProtocolDecision(
                status=DecisionStatus.TIMEOUT,
                step_id=current_step.step_id,
                step_number=current_step.step_number,
                observed_action=mapped_action,
                expected_actions=expected_actions,
                confidence=float(event.confidence),
                entropy=entropy,
                debounce_count=self._action_streak_count,
                debounce_threshold=self._default_debounce_threshold,
                explanation=(
                    f"Step '{current_step.step_id}' exceeded max timeout "
                    f"({elapsed_s:.1f}s > {current_step.timeouts.max_timeout_seconds}s)."
                ),
                evidence=evidence,
            )

        # 3. Invariant: High entropy or low confidence yields STEP_UNCERTAIN
        is_uncertain_status = (
            event.uncertainty_status in ("UNCERTAIN", "WARMING_UP", "DEGRADED")
            or event.confidence < min_conf
            or entropy > self._default_max_entropy
        )
        if is_uncertain_status:
            return ProtocolDecision(
                status=DecisionStatus.STEP_UNCERTAIN,
                step_id=current_step.step_id,
                step_number=current_step.step_number,
                observed_action=mapped_action,
                expected_actions=expected_actions,
                confidence=float(event.confidence),
                entropy=entropy,
                debounce_count=self._action_streak_count,
                debounce_threshold=self._default_debounce_threshold,
                explanation=(
                    f"Observation uncertain (confidence={event.confidence:.2f} < {min_conf:.2f} "
                    f"or entropy={entropy:.2f} > {self._default_max_entropy:.2f}). Awaiting clear evidence."
                ),
                evidence=evidence,
            )

        # 4. Invariant: UNKNOWN action yields WAITING_FOR_EVIDENCE, never violation
        if mapped_action == "unknown":
            return ProtocolDecision(
                status=DecisionStatus.WAITING_FOR_EVIDENCE,
                step_id=current_step.step_id,
                step_number=current_step.step_number,
                observed_action=mapped_action,
                expected_actions=expected_actions,
                confidence=float(event.confidence),
                entropy=entropy,
                debounce_count=self._action_streak_count,
                debounce_threshold=self._default_debounce_threshold,
                explanation="Observed activity is unrecognized or non-action. Waiting for procedure evidence.",
                evidence=evidence,
            )

        # Update action streak
        if mapped_action == self._last_observed_action:
            self._action_streak_count += 1
        else:
            self._last_observed_action = mapped_action
            self._action_streak_count = 1

        debounce_k = self._default_debounce_threshold

        # 5. Check if observed action satisfies expected action
        if mapped_action in expected_actions:
            if self._action_streak_count >= debounce_k:
                return ProtocolDecision(
                    status=DecisionStatus.VALID,
                    step_id=current_step.step_id,
                    step_number=current_step.step_number,
                    observed_action=mapped_action,
                    expected_actions=expected_actions,
                    confidence=float(event.confidence),
                    entropy=entropy,
                    debounce_count=self._action_streak_count,
                    debounce_threshold=debounce_k,
                    explanation=(
                        f"Action '{mapped_action}' matches expected step action with "
                        f"debounce streak {self._action_streak_count}/{debounce_k}."
                    ),
                    evidence=evidence,
                )
            return ProtocolDecision(
                status=DecisionStatus.WAITING_FOR_EVIDENCE,
                step_id=current_step.step_id,
                step_number=current_step.step_number,
                observed_action=mapped_action,
                expected_actions=expected_actions,
                confidence=float(event.confidence),
                entropy=entropy,
                debounce_count=self._action_streak_count,
                debounce_threshold=debounce_k,
                explanation=(
                    f"Observed matching action '{mapped_action}', debouncing: "
                    f"{self._action_streak_count}/{debounce_k} windows."
                ),
                evidence=evidence,
            )

        # 6. Action is not expected for current step.
        # If action is 'idle', treat as nominal waiting without deviation
        if mapped_action == "idle":
            return ProtocolDecision(
                status=DecisionStatus.WAITING_FOR_EVIDENCE,
                step_id=current_step.step_id,
                step_number=current_step.step_number,
                observed_action=mapped_action,
                expected_actions=expected_actions,
                confidence=float(event.confidence),
                entropy=entropy,
                debounce_count=self._action_streak_count,
                debounce_threshold=debounce_k,
                explanation="Astronaut is idle in workstation area. Waiting for step execution.",
                evidence=evidence,
            )

        # Check if the unexpected action is debounced before flagging skip/out-of-sequence
        if self._action_streak_count < debounce_k:
            return ProtocolDecision(
                status=DecisionStatus.WAITING_FOR_EVIDENCE,
                step_id=current_step.step_id,
                step_number=current_step.step_number,
                observed_action=mapped_action,
                expected_actions=expected_actions,
                confidence=float(event.confidence),
                entropy=entropy,
                debounce_count=self._action_streak_count,
                debounce_threshold=debounce_k,
                explanation=(
                    f"Transient unexpected action '{mapped_action}' observed "
                    f"({self._action_streak_count}/{debounce_k}); filtering potential noise."
                ),
                evidence=evidence,
            )

        # 7. Action is debounced and unexpected: First check for Wrong Object violation
        is_yellow_expected = any("yellow" in a for a in expected_actions)
        is_red_expected = any("red" in a for a in expected_actions)
        if (is_yellow_expected and "red" in mapped_action) or (
            is_red_expected and "yellow" in mapped_action
        ):
            return ProtocolDecision(
                status=DecisionStatus.WRONG_OBJECT,
                step_id=current_step.step_id,
                step_number=current_step.step_number,
                observed_action=mapped_action,
                expected_actions=expected_actions,
                confidence=float(event.confidence),
                entropy=entropy,
                debounce_count=self._action_streak_count,
                debounce_threshold=debounce_k,
                explanation=(
                    f"Wrong object manipulated! Expected {'Yellow Box' if is_yellow_expected else 'Red Box'}, "
                    f"but observed '{mapped_action}'."
                ),
                evidence=evidence,
            )

        # Determine if SKIPPED or OUT_OF_SEQUENCE
        # Check future steps (strictly subsequent)
        future_match_idx = None
        for idx in range(current_step_index + 1, len(spec.steps)):
            if mapped_action in [a.lower() for a in spec.steps[idx].expected_actions]:
                future_match_idx = idx
                break

        if future_match_idx is not None:
            skipped_steps = [
                spec.steps[i].step_id for i in range(current_step_index, future_match_idx)
            ]
            return ProtocolDecision(
                status=DecisionStatus.SKIPPED,
                step_id=current_step.step_id,
                step_number=current_step.step_number,
                observed_action=mapped_action,
                expected_actions=expected_actions,
                confidence=float(event.confidence),
                entropy=entropy,
                debounce_count=self._action_streak_count,
                debounce_threshold=debounce_k,
                explanation=(
                    f"Action '{mapped_action}' corresponds to future step "
                    f"'{spec.steps[future_match_idx].step_id}'. Intermediate steps "
                    f"{skipped_steps} were skipped."
                ),
                evidence=evidence,
                retroactive_skip_step_ids=skipped_steps,
            )

        # Check past steps
        past_match_idx = None
        for idx in range(current_step_index):
            if mapped_action in [a.lower() for a in spec.steps[idx].expected_actions]:
                past_match_idx = idx
                break

        if past_match_idx is not None:
            return ProtocolDecision(
                status=DecisionStatus.OUT_OF_SEQUENCE,
                step_id=current_step.step_id,
                step_number=current_step.step_number,
                observed_action=mapped_action,
                expected_actions=expected_actions,
                confidence=float(event.confidence),
                entropy=entropy,
                debounce_count=self._action_streak_count,
                debounce_threshold=debounce_k,
                explanation=(
                    f"Action '{mapped_action}' corresponds to previously completed step "
                    f"'{spec.steps[past_match_idx].step_id}' (out-of-sequence repetition)."
                ),
                evidence=evidence,
            )

        # General invalid action
        return ProtocolDecision(
            status=DecisionStatus.INVALID_ACTION,
            step_id=current_step.step_id,
            step_number=current_step.step_number,
            observed_action=mapped_action,
            expected_actions=expected_actions,
            confidence=float(event.confidence),
            entropy=entropy,
            debounce_count=self._action_streak_count,
            debounce_threshold=debounce_k,
            explanation=f"Action '{mapped_action}' does not match expected actions {expected_actions}.",
            evidence=evidence,
        )
