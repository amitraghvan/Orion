"""Temporal smoothing, uncertainty evaluation, and event phase translation for HAR."""

import math
from collections import deque

from orion_ai.activity.schemas import (
    TRAINED_ACTIVITY_CLASSES,
    ActivityPhase,
    UncertaintyStatus,
)


class TemporalPredictionSmoother:
    """Moving-average temporal smoother across consecutive window predictions per track."""

    def __init__(self, window_size: int = 5) -> None:
        self.window_size = window_size
        self._histories: dict[int, deque[dict[str, float]]] = {}

    def smooth(self, track_id: int, probs: dict[str, float]) -> dict[str, float]:
        """Record prediction and return exponentially or equally smoothed probability distribution."""
        if track_id not in self._histories:
            self._histories[track_id] = deque(maxlen=self.window_size)

        history = self._histories[track_id]
        history.append(probs)

        # Average probabilities across the smoothing deque
        smoothed: dict[str, float] = dict.fromkeys(TRAINED_ACTIVITY_CLASSES, 0.0)
        count = len(history)

        for p_dist in history:
            for cls, val in p_dist.items():
                smoothed[cls] = smoothed.get(cls, 0.0) + val / count

        # Normalize to ensure sum == 1.0
        total = sum(smoothed.values())
        if total > 0:
            smoothed = {k: v / total for k, v in smoothed.items()}

        return smoothed

    def evict_track(self, track_id: int) -> None:
        """Clear smoothing history for lost track."""
        self._histories.pop(track_id, None)

    def clear(self) -> None:
        """Reset all smoothing histories."""
        self._histories.clear()


class UncertaintyEvaluator:
    """Epistemic uncertainty and entropy evaluator for classification distributions."""

    def __init__(
        self,
        entropy_threshold: float = 1.4,
        confidence_threshold: float = 0.5,
    ) -> None:
        self.entropy_threshold = entropy_threshold
        self.confidence_threshold = confidence_threshold

    def evaluate(
        self,
        probs: dict[str, float],
        is_warming_up: bool = False,
        is_degraded: bool = False,
        has_track: bool = True,
    ) -> tuple[UncertaintyStatus, float]:
        """Compute distribution entropy and determine epistemic status.

        Returns:
            (status, entropy_value)
        """
        if not has_track:
            return UncertaintyStatus.UNKNOWN, 0.0

        if is_warming_up:
            return UncertaintyStatus.WARMING_UP, 0.0

        # Calculate Shannon entropy H(p) = -sum(p * ln(p))
        entropy = 0.0
        eps = 1e-9
        for p in probs.values():
            if p > eps:
                entropy -= p * math.log(p)

        if is_degraded:
            return UncertaintyStatus.DEGRADED, float(entropy)

        max_prob = max(probs.values()) if probs else 0.0

        if max_prob < self.confidence_threshold or entropy > self.entropy_threshold:
            return UncertaintyStatus.UNCERTAIN, float(entropy)

        return UncertaintyStatus.NOMINAL, float(entropy)


class ActivityEventTranslator:
    """Translates frame-by-frame recognized states into semantic lifecycle events (START, UPDATE, CHANGE, END)."""

    def __init__(self, rate_limit_frames: int = 4) -> None:
        self.rate_limit_frames = rate_limit_frames
        self._last_activity: dict[int, str] = {}
        self._last_emitted_frame: dict[int, int] = {}
        self._active_tracks: set[int] = set()

    def translate(
        self,
        track_id: int,
        activity_name: str,
        frame_index: int,
    ) -> tuple[ActivityPhase, bool]:
        """Determine the activity phase and whether a telemetry event should be emitted.

        Returns:
            (phase, should_emit)
        """
        if track_id not in self._last_activity:
            self._last_activity[track_id] = activity_name
            self._last_emitted_frame[track_id] = frame_index
            self._active_tracks.add(track_id)
            return ActivityPhase.START, True

        last_act = self._last_activity[track_id]

        if activity_name != last_act:
            self._last_activity[track_id] = activity_name
            self._last_emitted_frame[track_id] = frame_index
            return ActivityPhase.CHANGE, True

        # Same activity: check rate-limiting
        last_emitted = self._last_emitted_frame.get(track_id, 0)
        frames_elapsed = frame_index - last_emitted

        if frames_elapsed >= self.rate_limit_frames:
            self._last_emitted_frame[track_id] = frame_index
            return ActivityPhase.UPDATE, True

        return ActivityPhase.UPDATE, False

    def end_track(self, track_id: int) -> tuple[str, ActivityPhase] | None:
        """Signal activity termination when track is dropped or evicted."""
        if track_id in self._last_activity:
            last_act = self._last_activity.pop(track_id)
            self._last_emitted_frame.pop(track_id, None)
            self._active_tracks.discard(track_id)
            return last_act, ActivityPhase.END
        return None

    def clear(self) -> None:
        """Reset all track state trackers."""
        self._last_activity.clear()
        self._last_emitted_frame.clear()
        self._active_tracks.clear()
