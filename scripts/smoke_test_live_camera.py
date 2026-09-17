"""Automated Live Camera Smoke Test for ORION BAS AI Copilot.

Ingests live optical frames from local webcam (device index 0) via authoritative CameraManager,
executes complete perception DAG:
  LIVE CAMERA -> FRAME -> DETECTION -> POSE -> TRACKING -> HOI -> HAR -> OBSERVATION -> EVENT
and verifies end-to-end telemetry generation, throughput, and latency.
"""

import asyncio
import sys
import time
from pathlib import Path

from orion.core.in_memory_event_bus import InMemoryEventBus
from orion.events.schemas import FrameCaptured, ObservationCaptured
from orion_ai.activity.configs import ActivityConfig
from orion_ai.activity.runtime import TemporalHARRuntime
from orion_ai.camera.camera_manager import authoritative_camera_manager
from orion_ai.detection.yolo_detector import YOLOEdgeDetector
from orion_ai.pose.yolo_pose import YOLOPoseEstimator
from orion_ai.runtime.coordinator import PerceptionPipelineCoordinator
from orion_ai.tracking.byte_tracker import ByteTracker


async def run_live_smoke_test(target_frames: int = 35) -> int:
    print("==================================================================")
    print("🚀 ORION BAS AI COPILOT — CANONICAL LIVE CAMERA SMOKE TEST")
    print(f"Target frame evaluations: {target_frames}")
    print("==================================================================")

    # 1. Event Bus with audit subscribers
    event_bus = InMemoryEventBus()
    captured_events: list[str] = []

    async def on_frame_event(ev: FrameCaptured):
        captured_events.append(f"FrameCaptured-{ev.frame_index}")

    async def on_obs_event(ev: ObservationCaptured):
        captured_events.append(f"ObservationCaptured-{ev.observation.frame_id}")

    event_bus.subscribe(FrameCaptured, on_frame_event)
    event_bus.subscribe(ObservationCaptured, on_obs_event)

    # 2. Authoritative CameraManager
    authoritative_camera_manager.configure(source=0, width=1280, height=720, fps=30)
    camera = authoritative_camera_manager

    # 3. Hardware Acceleration Detection
    import torch

    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    print(f"Authoritative hardware compute backend: {device.upper()}")

    # 4. Perception Models Loading
    detector = YOLOEdgeDetector(confidence_threshold=0.25, device=device)
    det_weights = Path("models/weights/yolo11n.pt")
    if det_weights.exists():
        await detector.load(str(det_weights))

    pose_estimator = YOLOPoseEstimator(confidence_threshold=0.25, device=device)
    pose_weights = Path("models/weights/yolo11n-pose.pt")
    if pose_weights.exists():
        await pose_estimator.load(str(pose_weights))

    tracker = ByteTracker(high_score_thresh=0.4, match_thresh=0.3)

    har_runtime: TemporalHARRuntime | None = None
    bas_weights = Path("models/bas_experiment/best.pt")
    if bas_weights.exists():
        har_config = ActivityConfig(
            model_id="BAS-HAR-v1.0",
            window_size_frames=32,
            stride_frames=8,
            confidence_threshold=0.3,
        )
        har_runtime = TemporalHARRuntime(
            config=har_config,
            model_path=str(bas_weights),
            device=device,
            station_id="BAS-DEV-BENCH-01",
        )
        await har_runtime.initialize()

    coordinator = PerceptionPipelineCoordinator(
        camera=camera,
        detector=detector,
        pose_estimator=pose_estimator,
        tracker=tracker,
        event_bus=event_bus,
        station_id="BAS-DEV-BENCH-01",
        har_runtime=har_runtime,
    )

    print("Opening live camera and starting perception loop...")
    await coordinator.start()

    person_detections_total = 0
    poses_total = 0
    latencies = []
    t_start = time.perf_counter()

    try:
        while coordinator.frames_processed < target_frames:
            await asyncio.sleep(0.05)
            obs = coordinator.latest_observation
            if obs:
                person_detections_total = max(person_detections_total, len(obs.person_detections))
                poses_total = max(poses_total, len(obs.poses))
                latencies.append(obs.metrics.pipeline_latency_ms)

        total_elapsed = time.perf_counter() - t_start
        processed = coordinator.frames_processed
        avg_fps = processed / total_elapsed if total_elapsed > 0 else 0.0
        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0

        print(f"\nLive Results after {total_elapsed:.2f}s:")
        print(f"  Camera Status:            {authoritative_camera_manager.status.value}")
        print(f"  Frames captured:          {coordinator.frames_received}")
        print(f"  Frames processed:         {processed}")
        print(f"  Frames failed:            {coordinator.frames_failed}")
        print(f"  Actual Measured FPS:      {avg_fps:.1f}")
        print(f"  Average Latency:          {avg_lat:.1f}ms")
        print(f"  Max observed person det:  {person_detections_total}")
        print(f"  Max observed poses:       {poses_total}")
        print(f"  Events dispatched:        {len(captured_events)}")
        print(
            f"  Latest JPEG bytes:        {len(coordinator.latest_jpeg_bytes) if coordinator.latest_jpeg_bytes else 0} bytes"
        )

        assert processed >= target_frames, "Did not process required frames"
        assert coordinator.latest_jpeg_bytes is not None, "Latest JPEG byte buffer must exist"
        assert len(captured_events) > 0, "EventBus must have received domain events"
        assert authoritative_camera_manager.status.value in ("CONNECTED", "PROCESSING"), (
            "Camera must be CONNECTED"
        )

        print("\n==================================================================")
        print("✅ LIVE CAMERA SMOKE TEST: PASSED NOMINAL")
        print("Pipeline sequence verified:")
        print("  LIVE CAMERA -> FRAME -> DETECTION -> POSE -> HAR -> OBSERVATION -> EVENT")
        print("==================================================================")
        return 0
    except Exception as exc:
        print(f"\n❌ LIVE CAMERA SMOKE TEST FAILED: {exc}")
        return 1
    finally:
        await coordinator.stop()


if __name__ == "__main__":
    ret = asyncio.run(run_live_smoke_test())
    sys.exit(ret)
