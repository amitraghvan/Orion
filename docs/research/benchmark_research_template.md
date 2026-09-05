# Research Template: Hardware & Latency Benchmarks

## 1. Objective
Benchmarking perception pipeline latency, FPS throughput, and thermal stability on target spaceflight compute nodes.

## 2. Methodology
- 1,000-frame warmup phase.
- 10,000-frame sustained continuous inference loop.
- Measuring p50, p90, p95, p99 end-to-end frame turnaround latency.

## 3. Telemetry Log
| Accelerator | Batch Size | Precision | Latency p50 (ms) | Latency p99 (ms) | FPS | GPU Mem (MB) | Peak Temp (°C) |
|---|---|---|---|---|---|---|---|
| Jetson AGX Orin | 1 | INT8 | - | - | - | - | - |
| Jetson AGX Orin | 1 | FP16 | - | - | - | - | - |
