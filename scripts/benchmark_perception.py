"""Perception and ST-GCN Temporal HAR performance and memory benchmark script for ORION BAS AI Copilot."""

import asyncio
import os
import time
from pathlib import Path

import psutil

from orion.core.in_memory_event_bus import InMemoryEventBus
from orion.events.schemas import BaseEvent
from orion_ai.activity.configs import ActivityConfig
from orion_ai.activity.runtime import TemporalHARRuntime
from orion_ai.camera.opencv_driver import OpenCVCameraDriver
from orion_ai.detection.yolo_detector import YOLOEdgeDetector
from orion_ai.pose.yolo_pose import YOLOPoseEstimator
from orion_ai.runtime.coordinator import PerceptionPipelineCoordinator
from orion_ai.tracking.byte_tracker import ByteTracker


async def run_benchmark(num_frames: int = 60) -> None:
    process = psutil.Process(os.getpid())
    rss_start_mb = process.memory_info().rss / (1024 * 1024)

    video_path = Path("assets/sample_replay.mp4")
    det_weights = Path("models/weights/yolo11n.pt")
    pose_weights = Path("models/weights/yolo11n-pose.pt")
    har_weights = Path("models/weights/stgcn_har_v1.pt")

    event_bus = InMemoryEventBus()
    event_counter = 0

    async def _counter_listener(_: BaseEvent) -> None:
        nonlocal event_counter
        event_counter += 1

    event_bus.subscribe(BaseEvent, _counter_listener)

    camera = OpenCVCameraDriver(
        source=str(video_path),
        camera_id="benchmark_cam",
        target_fps=0,
        width=640,
        height=480,
        loop=True,
    )
    detector = YOLOEdgeDetector(confidence_threshold=0.25, device="cpu")
    pose_estimator = YOLOPoseEstimator(confidence_threshold=0.25, device="cpu")
    tracker = ByteTracker(high_score_thresh=0.4, match_thresh=0.3)

    har_config = ActivityConfig(
        model_id="stgcn_har_v1",
        window_size_frames=32,
        stride_frames=8,
        confidence_threshold=0.3,
    )
    har_runtime = TemporalHARRuntime(
        config=har_config,
        model_path=str(har_weights),
        device="cpu",
        station_id="BAS-BENCHMARK",
    )

    print("Initializing camera and loading perception + HAR models...")
    await camera.initialize()
    await detector.load(str(det_weights))
    await pose_estimator.load(str(pose_weights))
    await har_runtime.initialize()

    coordinator = PerceptionPipelineCoordinator(
        camera=camera,
        detector=detector,
        pose_estimator=pose_estimator,
        tracker=tracker,
        event_bus=event_bus,
        station_id="BAS-BENCHMARK",
        har_runtime=har_runtime,
    )

    cam_latencies: list[float] = []
    det_latencies: list[float] = []
    pose_latencies: list[float] = []
    track_latencies: list[float] = []
    har_latencies: list[float] = []
    total_latencies: list[float] = []
    recognized_activities_count = 0

    print(f"Running full perception + HAR benchmark on {num_frames} frames...")
    wall_start = time.perf_counter()

    for _ in range(num_frames):
        obs = await coordinator.process_single_frame()
        cam_latencies.append(obs.metrics.camera_latency_ms)
        det_latencies.append(obs.metrics.detection_latency_ms)
        pose_latencies.append(obs.metrics.pose_latency_ms)
        track_latencies.append(obs.metrics.tracking_latency_ms)
        har_latencies.append(obs.metrics.har_latency_ms or 0.0)
        total_latencies.append(obs.metrics.pipeline_latency_ms)
        if obs.activities:
            recognized_activities_count += len(obs.activities)

    wall_duration = time.perf_counter() - wall_start
    rss_end_mb = process.memory_info().rss / (1024 * 1024)
    rss_delta_mb = rss_end_mb - rss_start_mb

    await camera.shutdown()
    await detector.unload()
    await pose_estimator.unload()
    await har_runtime.shutdown()
    await event_bus.shutdown()

    fps = num_frames / wall_duration
    mean_cam = sum(cam_latencies) / len(cam_latencies)
    mean_det = sum(det_latencies) / len(det_latencies)
    mean_pose = sum(pose_latencies) / len(pose_latencies)
    mean_track = sum(track_latencies) / len(track_latencies)
    # Average HAR latency on frames where stride triggered (non-zero)
    active_har_latencies = [lat for lat in har_latencies if lat > 0.0]
    mean_har_active = sum(active_har_latencies) / len(active_har_latencies) if active_har_latencies else 0.0
    mean_har_all = sum(har_latencies) / len(har_latencies)
    mean_total = sum(total_latencies) / len(total_latencies)

    print("\n" + "=" * 65)
    print("ORION PHASE 1.3 TEMPORAL HAR BENCHMARK RESULTS")
    print("=" * 65)
    print(f"Frames Processed:           {num_frames}")
    print(f"Wall Duration:              {wall_duration:.2f} s")
    print(f"Effective Pipeline FPS:     {fps:.2f} FPS")
    print(f"Mean Camera Latency:        {mean_cam:.2f} ms")
    print(f"Mean Detection Latency:     {mean_det:.2f} ms")
    print(f"Mean Pose Latency:          {mean_pose:.2f} ms")
    print(f"Mean Tracking Latency:      {mean_track:.2f} ms")
    print(f"Mean Active HAR Latency:    {mean_har_active:.2f} ms (on stride triggers)")
    print(f"Mean Overall HAR Latency:   {mean_har_all:.2f} ms (amortized across frames)")
    print(f"Mean Total Pipeline:        {mean_total:.2f} ms")
    print(f"Initial Process RSS:        {rss_start_mb:.1f} MB")
    print(f"Final Process RSS:          {rss_end_mb:.1f} MB")
    print(f"Process RSS Delta:          {rss_delta_mb:+.1f} MB")
    print(f"Total Dispatched Events:    {event_counter}")
    print(f"Total Activities Evaluated: {recognized_activities_count}")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(run_benchmark(60))
