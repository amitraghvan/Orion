"""Automated end-to-end perception and inference latency benchmark suite."""

from __future__ import annotations

import time
import numpy as np
import psutil

from app.core.paths import paths
from app.models.model_manager import model_manager
from app.intelligence.tracker import ObjectTrackerWrapper
from app.intelligence.hand_object_engine import HandObjectInteractionEngine
from app.experiments.experiment_loader import load_protocol
from app.intelligence.decision_engine import ProtocolDecisionEngine


def run_benchmark(iterations: int = 50) -> dict:
    print("==================================================================")
    print(" ORION PRODUCTION BENCHMARK SUITE")
    print(f" Iterations: {iterations}")
    print("==================================================================\n")

    # Load models
    det_path = paths.resolve_model_path("yolo11n.pt")
    pose_path = paths.resolve_model_path("yolo11n-pose.pt")
    har_path = paths.resolve_model_path("best.pt")

    model_manager.load_model("det", det_path)
    model_manager.load_model("pose", pose_path)
    model_manager.load_model("har", har_path)

    det_m = model_manager.get_model("det")
    pose_m = model_manager.get_model("pose")
    har_m = model_manager.get_model("har")

    tracker = ObjectTrackerWrapper()
    hoi = HandObjectInteractionEngine()
    spec = load_protocol("configs/protocols/bas_e01_a.yaml")
    decision_engine = ProtocolDecisionEngine()

    dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    dummy_seq = np.zeros((1, 4, 32, 17), dtype=np.float32)

    # 1. Benchmark Detection
    t_det = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        if det_m:
            det_m.predict(dummy_frame)
        t_det.append((time.perf_counter() - t0) * 1000.0)

    # 2. Benchmark Pose
    t_pose = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        if pose_m:
            pose_m.predict(dummy_frame)
        t_pose.append((time.perf_counter() - t0) * 1000.0)

    # 3. Benchmark HAR
    t_har = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        if har_m:
            har_m.predict(dummy_seq)
        t_har.append((time.perf_counter() - t0) * 1000.0)

    # 4. Benchmark Tracking & HOI
    dummy_dets = [
        {"bbox": [100, 100, 200, 200], "confidence": 0.9, "class_id": 0, "class_name": "person"},
        {"bbox": [300, 300, 380, 380], "confidence": 0.85, "class_id": 1, "class_name": "yellow_box"},
    ]
    t_track = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        tracker.update(dummy_dets)
        t_track.append((time.perf_counter() - t0) * 1000.0)

    # 5. Benchmark Sequence Decision
    t_decision = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        decision_engine.evaluate("pick_yellow", 0.95, 0.20, spec, current_step_index=0)
        t_decision.append((time.perf_counter() - t0) * 1000.0)

    med_det = float(np.median(t_det))
    med_pose = float(np.median(t_pose))
    med_har = float(np.median(t_har))
    med_trk = float(np.median(t_track))
    med_dec = float(np.median(t_decision))
    e2e = med_det + med_pose + med_har + med_trk + med_dec

    results = {
        "detection_latency_ms": round(med_det, 2),
        "pose_latency_ms": round(med_pose, 2),
        "har_latency_ms": round(med_har, 2),
        "tracking_latency_ms": round(med_trk, 3),
        "decision_latency_ms": round(med_dec, 3),
        "total_pipeline_latency_ms": round(e2e, 2),
        "throughput_fps": round(1000.0 / e2e, 1) if e2e > 0 else 0.0,
        "cpu_percent": psutil.cpu_percent(),
        "ram_percent": psutil.virtual_memory().percent,
    }

    print("------------------------------------------------------------------")
    print(f" Detection Latency (median):     {results['detection_latency_ms']} ms")
    print(f" Pose Latency (median):          {results['pose_latency_ms']} ms")
    print(f" ST-GCN HAR Latency (median):    {results['har_latency_ms']} ms")
    print(f" Tracking & HOI (median):        {results['tracking_latency_ms']} ms")
    print(f" Protocol Decision (median):     {results['decision_latency_ms']} ms")
    print(f" End-to-End Latency:             {results['total_pipeline_latency_ms']} ms")
    print(f" Equivalent AI Throughput:       {results['throughput_fps']} FPS")
    print(f" CPU Load:                       {results['cpu_percent']}%")
    print(f" RAM Load:                       {results['ram_percent']}%")
    print("------------------------------------------------------------------\n")

    return results


if __name__ == "__main__":
    run_benchmark(30)
