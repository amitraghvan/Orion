"""Unit tests for temporal smoothing, uncertainty evaluation, and event phase translation."""

import pytest

from orion_ai.activity.schemas import ActivityPhase, UncertaintyStatus
from orion_ai.activity.smoothing import (
    ActivityEventTranslator,
    TemporalPredictionSmoother,
    UncertaintyEvaluator,
)


def test_temporal_prediction_smoother_moving_average() -> None:
    smoother = TemporalPredictionSmoother(window_size=3)
    track_id = 1

    # Step 1: idle 1.0
    p1 = {"idle": 1.0, "reach_tool": 0.0}
    s1 = smoother.smooth(track_id, p1)
    assert s1["idle"] == pytest.approx(1.0)

    # Step 2: sudden noise spike for reach_tool 1.0
    p2 = {"idle": 0.0, "reach_tool": 1.0}
    s2 = smoother.smooth(track_id, p2)
    # Smoothed over 2 samples: (1.0 + 0.0)/2 = 0.5
    assert s2["idle"] == pytest.approx(0.5)
    assert s2["reach_tool"] == pytest.approx(0.5)

    # Step 3: return to idle
    p3 = {"idle": 1.0, "reach_tool": 0.0}
    s3 = smoother.smooth(track_id, p3)
    # Average of [1.0, 0.0, 1.0] -> 2/3 approx 0.667
    assert s3["idle"] == pytest.approx(2.0 / 3.0)
    assert s3["reach_tool"] == pytest.approx(1.0 / 3.0)

    # Evict track
    smoother.evict_track(track_id)
    s_new = smoother.smooth(track_id, {"reach_tool": 1.0})
    assert s_new["reach_tool"] == pytest.approx(1.0)


def test_uncertainty_evaluator_entropy_and_states() -> None:
    evaluator = UncertaintyEvaluator(entropy_threshold=1.4, confidence_threshold=0.5)

    # 1. Peaked distribution (low entropy, high confidence) -> NOMINAL
    peaked = {
        "prepare_workstation": 0.02,
        "reach_tool": 0.90,
        "grasp_tool": 0.03,
        "manipulate_sample": 0.02,
        "inspect_chamber": 0.02,
        "idle": 0.01,
    }
    status, ent = evaluator.evaluate(peaked)
    assert status == UncertaintyStatus.NOMINAL
    assert ent < 1.0

    # 2. Uniform flat distribution (max entropy ln(6) ~ 1.79 > 1.4) -> UNCERTAIN
    uniform = {
        "prepare_workstation": 1.0 / 6.0,
        "reach_tool": 1.0 / 6.0,
        "grasp_tool": 1.0 / 6.0,
        "manipulate_sample": 1.0 / 6.0,
        "inspect_chamber": 1.0 / 6.0,
        "idle": 1.0 / 6.0,
    }
    status_u, ent_u = evaluator.evaluate(uniform)
    assert status_u == UncertaintyStatus.UNCERTAIN
    assert ent_u > 1.7

    # 3. Degraded input flag -> DEGRADED
    status_deg, _ = evaluator.evaluate(peaked, is_degraded=True)
    assert status_deg == UncertaintyStatus.DEGRADED

    # 4. Warming up flag -> WARMING_UP
    status_warm, _ = evaluator.evaluate(peaked, is_warming_up=True)
    assert status_warm == UncertaintyStatus.WARMING_UP

    # 5. Missing track -> UNKNOWN
    status_unk, _ = evaluator.evaluate(peaked, has_track=False)
    assert status_unk == UncertaintyStatus.UNKNOWN


def test_activity_event_translator_lifecycle_and_rate_limiting() -> None:
    translator = ActivityEventTranslator(rate_limit_frames=4)
    track_id = 42

    # Frame 0: First recognition -> START (emits immediately)
    phase, emit = translator.translate(track_id, "reach_tool", frame_index=0)
    assert phase == ActivityPhase.START
    assert emit is True

    # Frame 1: Same activity, only 1 frame elapsed (< 4) -> UPDATE, emit is False
    phase, emit = translator.translate(track_id, "reach_tool", frame_index=1)
    assert phase == ActivityPhase.UPDATE
    assert emit is False

    # Frame 4: 4 frames elapsed -> UPDATE, emit is True
    phase, emit = translator.translate(track_id, "reach_tool", frame_index=4)
    assert phase == ActivityPhase.UPDATE
    assert emit is True

    # Frame 5: Activity changes to grasp_tool -> CHANGE (emits immediately)
    phase, emit = translator.translate(track_id, "grasp_tool", frame_index=5)
    assert phase == ActivityPhase.CHANGE
    assert emit is True

    # Track ends -> END
    end_res = translator.end_track(track_id)
    assert end_res is not None
    act_name, end_phase = end_res
    assert act_name == "grasp_tool"
    assert end_phase == ActivityPhase.END
