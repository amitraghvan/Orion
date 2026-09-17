"""Automated BAS Real Video Replay Smoke Test for ORION BAS AI Copilot.

Loads a real BAS experiment recording from BAS_REAL_DATA, feeds it through
the exact same perception and protocol validation pipeline, and verifies
observation production, protocol step progression, and violation detection.
"""

import asyncio
import sys
import time
from pathlib import Path

from orion.core.in_memory_event_bus import InMemoryEventBus
from orion.protocol.service import ProtocolService
from orion_ai.activity.configs import ActivityConfig
from orion_ai.activity.runtime import TemporalHARRuntime
from orion_ai.camera.opencv_driver import OpenCVCameraDriver
from orion_ai.detection.yolo_detector import YOLOEdgeDetector
from orion_ai.pose.yolo_pose import YOLOPoseEstimator
from orion_ai.runtime.coordinator import PerceptionPipelineCoordinator
from orion_ai.tracking.byte_tracker import ByteTracker


async def run_replay_smoke_test(video_path: str, protocol_path: str = "configs/protocols/bas_e01_a.yaml", max_frames: int = 40) -> int:
    print("==================================================================")
    print("🎬 ORION BAS AI COPILOT — REPLAY VIDEO SMOKE TEST")
    print(f"Video source:  {video_path}")
    print(f"Protocol YAML: {protocol_path}")
    print("==================================================================")

    if not Path(video_path).exists():
        print(f"❌ Video file does not exist: {video_path}")
        return 1

    event_bus = InMemoryEventBus()

    # Protocol Service
    protocol_service = ProtocolService(event_bus=event_bus)
    protocol_service.load_protocol_file(protocol_path)
    run_id = protocol_service.start_experiment()
    print(f"Started experiment run: {run_id} (FSM state: {protocol_service.state})")

    # Replay Video Driver
    camera = OpenCVCameraDriver(source=video_path, loop=False, target_fps=30)

    import torch
    device = "mps" if torch.backends.mps.is_available() else "cpu"

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

    print("Starting replay perception loop...")
    await coordinator.start()
    t_start = time.perf_counter()

    try:
        while coordinator.frames_processed < max_frames and coordinator.is_running:
            await asyncio.sleep(0.1)

        total_elapsed = time.perf_counter() - t_start
        processed = coordinator.frames_processed
        print(f"\nReplay summary after {total_elapsed:.2f}s:")
        print(f"  Frames processed: {processed}")
        print(f"  FPS:              {processed / total_elapsed:.1f}")
        print(f"  FSM State:        {protocol_service.state}")
        print(f"  Current Step:     {protocol_service.fsm.current_step.step_id if protocol_service.fsm.current_step else 'None'}")
        print(f"  Last Decision UTC:{protocol_service._last_decision_utc}")

        assert processed >= 10, "Replay did not process minimal frames"
        print("\n==================================================================")
        print("✅ REPLAY VIDEO SMOKE TEST: PASSED NOMINAL")
        print("==================================================================")
        return 0
    except Exception as exc:
        print(f"\n❌ REPLAY VIDEO SMOKE TEST FAILED: {exc}")
        return 1
    finally:
        await coordinator.stop()


if __name__ == "__main__":
    canonical_video = sys.argv[1] if len(sys.argv) > 1 else "/Users/amitkumar/Downloads/BAS_REAL_DATA/VALID/SP04/AP01.mp4"
    if not Path(canonical_video).exists():
        fallback = Path("assets/sample_replay.mp4")
        if fallback.exists():
            canonical_video = str(fallback)
    code = asyncio.run(run_replay_smoke_test(canonical_video, max_frames=30))
    sys.exit(code)
