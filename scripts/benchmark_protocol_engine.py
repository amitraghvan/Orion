"""Benchmark stress testing ORION Protocol Decision Engine under 10,000 events."""

from __future__ import annotations

import statistics
import time

from experiments.loader import load_protocol

from orion.events.schemas import ActivityRecognized
from orion.protocol.decision_engine import ProtocolDecisionEngine


def run_benchmark(num_events: int = 10000) -> None:
    print("\n========================================================")
    print(" ORION BAS AI COPILOT — PROTOCOL ENGINE BENCHMARK")
    print(f" Target Event Count: {num_events:,}")
    print("========================================================\n")

    spec = load_protocol("configs/protocols/bas_crystal_growth_v1.yaml")
    engine = ProtocolDecisionEngine()
    engine.reset_step()

    # Pre-generate 10,000 synthetic events
    actions = [
        "prepare_workstation",
        "reach_tool",
        "grasp_tool",
        "manipulate_sample",
        "inspect_chamber",
        "idle",
    ]

    synthetic_events = [
        ActivityRecognized(
            track_id=1,
            window_start_frame=i * 32,
            window_end_frame=(i + 1) * 32,
            activity_label=actions[i % len(actions)],
            confidence=0.85 + (i % 10) * 0.01,
            evidence_metadata={
                "entropy": 0.35 + (i % 20) * 0.01,
                "probabilities": {actions[i % len(actions)]: 0.85},
            },
        )
        for i in range(num_events)
    ]

    # Warm-up (100 events)
    for i in range(100):
        engine.evaluate(synthetic_events[i], spec, current_step_index=0)
    engine.reset_step()

    # Timed benchmark loop
    latencies_ms: list[float] = []
    t_start = time.perf_counter()

    for event in synthetic_events:
        t0 = time.perf_counter()
        _ = engine.evaluate(event, spec, current_step_index=0)
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    total_time_s = time.perf_counter() - t_start
    throughput = num_events / total_time_s

    latencies_sorted = sorted(latencies_ms)
    p50 = statistics.median(latencies_ms)
    p95 = latencies_sorted[int(num_events * 0.95)]
    p99 = latencies_sorted[int(num_events * 0.99)]
    avg_latency = statistics.mean(latencies_ms)

    print("--------------------------------------------------------")
    print(" BENCHMARK RESULTS")
    print("--------------------------------------------------------")
    print(f" Total Events Processed: {num_events:,}")
    print(f" Total Wall Time:        {total_time_s:.4f} s")
    print(f" Sustained Throughput:   {throughput:,.1f} events/sec")
    print(f" Mean Latency:           {avg_latency:.4f} ms")
    print(f" P50 Latency:            {p50:.4f} ms")
    print(f" P95 Latency:            {p95:.4f} ms")
    print(f" P99 Latency:            {p99:.4f} ms")
    print("--------------------------------------------------------")
    assert throughput > 1000, f"Throughput {throughput} events/s below required threshold (>1000)"
    print("✓ Protocol Decision Engine passed high-throughput SLA verification!\n")


if __name__ == "__main__":
    run_benchmark(10000)
