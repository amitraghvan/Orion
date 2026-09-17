"""Confidence calibration, entropy evaluation, and safety invariants."""

from __future__ import annotations


class ConfidenceManager:
    """Enforces confidence thresholds, entropy gating, and safety invariants."""

    def __init__(
        self,
        min_confidence: float = 0.65,
        max_entropy: float = 1.40,
        debounce_threshold: int = 2,
    ) -> None:
        self.min_confidence = min_confidence
        self.max_entropy = max_entropy
        self.debounce_threshold = debounce_threshold

    def evaluate_evidence_quality(
        self,
        action: str,
        confidence: float,
        entropy: float,
        streak_count: int,
    ) -> tuple[str, bool]:
        """Assess whether an action observation qualifies as confirmed evidence.

        Returns (assessment_status, is_confirmed):
        - assessment_status: "CONFIRMED", "WAITING_FOR_EVIDENCE", "UNCERTAIN"
        - is_confirmed: True if confidence >= min_conf, entropy <= max_entropy, and streak >= threshold
        """
        # Invariant 1: Low confidence or high entropy is UNCERTAIN, not a violation
        if confidence < self.min_confidence or entropy > self.max_entropy:
            return "UNCERTAIN", False

        # Invariant 2: Single-frame detection is unconfirmed debouncing
        if streak_count < self.debounce_threshold:
            return "WAITING_FOR_EVIDENCE", False

        return "CONFIRMED", True
