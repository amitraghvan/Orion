"""Unit tests for STGCNActivityClassifier."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
import torch

from orion_ai.activity.schemas import (
    ActivityPhase,
    ActivityWindow,
    BoundingBox2D,
    KeypointState,
    TemporalKeypoint,
    TemporalSkeletonPose,
    UncertaintyStatus,
)
from orion_ai.activity.stgcn_classifier import STGCNActivityClassifier
from orion_ai.activity.training.dataset import SyntheticKinematicGenerator


@pytest.mark.asyncio
async def test_stgcn_classifier_lifecycle_and_inference() -> None:
    weights_path = Path("models/weights/stgcn_har_v1.pt")
    if not weights_path.exists():
        pytest.skip("ST-GCN weights file not found.")

    classifier = STGCNActivityClassifier(device="cpu", confidence_threshold=0.5)
    await classifier.load(str(weights_path))

    gen = SyntheticKinematicGenerator(num_frames=32, seed=42)
    sample_tensor, _label, _ = gen.generate_sample("reach_tool")

    # 1. Classify tensor directly
    result = await classifier.classify_window(sample_tensor)
    assert result.top_prediction is not None
    assert result.top_prediction.activity_name in [
        "prepare_workstation",
        "reach_tool",
        "grasp_tool",
        "manipulate_sample",
        "inspect_chamber",
        "idle",
    ]
    assert 0.0 <= result.top_prediction.confidence <= 1.0
    assert len(result.candidates) == 6
    assert result.latency_ms >= 0.0

    # 2. Classify list of TemporalSkeletonPose
    poses: list[TemporalSkeletonPose] = []
    bbox = BoundingBox2D(x_min=100.0, y_min=100.0, x_max=300.0, y_max=500.0, confidence=0.95)
    now = datetime.now(UTC)

    for f_idx in range(32):
        kpts = [
            TemporalKeypoint(
                id=i,
                name=f"joint_{i}",
                x=200.0 + i * 2,
                y=250.0 + i * 5,
                score=0.9,
                state=KeypointState.OBSERVED,
            )
            for i in range(17)
        ]
        poses.append(
            TemporalSkeletonPose(
                frame_index=f_idx,
                timestamp_utc=now,
                track_id=1,
                bbox=bbox,
                keypoints_2d=kpts,
                overall_confidence=0.9,
            )
        )

    window = ActivityWindow(
        start_frame=0,
        end_frame=31,
        fps=30,
        duration_seconds=32 / 30.0,
        stride=8,
        track_id=1,
    )
    result_pose = await classifier.classify_window(poses, window=window)
    assert result_pose.track_id == 1
    assert result_pose.window.stride == 8
    assert result_pose.top_prediction.activity_name in [
        "prepare_workstation",
        "reach_tool",
        "grasp_tool",
        "manipulate_sample",
        "inspect_chamber",
        "idle",
    ]

    # 3. Concurrency test: 5 parallel inferences
    tasks = [classifier.classify_window(sample_tensor) for _ in range(5)]
    results = await asyncio.gather(*tasks)
    assert len(results) == 5
    for res in results:
        assert res.top_prediction.confidence > 0.0

    # 4. Unload
    await classifier.unload()
    assert classifier.model is None
