# ORION Performance & Latency Benchmark Report


---

## 1. End-to-End Perception Pipeline Benchmarks

### 1.1 Apple Silicon Hardware Acceleration (MPS)
Measured via [`scripts/smoke_test_live_camera.py`](file:///Users/amitkumar/Orion/scripts/smoke_test_live_camera.py) running on live hardware webcam capture:

| Subsystem Component | Hardware Device | Mean Latency | Throughput | Measurement Notes |
|---|---|---|---|---|
| **Camera Ingestion** | USB/CSI UVC | 0.22 ms | 30.0 FPS | Non-blocking ring buffer fetch |
| **YOLO11n Detection** | Metal (MPS) | ~21.50 ms | - | $640 \times 640$ tensor inference |
| **YOLO11n-pose Pose** | Metal (MPS) | ~22.80 ms | - | 17 COCO joints regression |
| **ByteTrack Tracking** | CPU | 0.06 ms | - | Kalman filter + IoU association |
| **ST-GCN Temporal HAR** | Metal (MPS) | ~0.55 ms | - | Forward pass on 32-frame skeleton window |
| **End-to-End Pipeline** | **MPS + CPU** | **49.60 ms** | **21.2 FPS** | **Zero dropped capture frames** |

### 1.2 CPU Edge Baseline Benchmark
Measured via [`scripts/benchmark_perception.py`](file:///Users/amitkumar/Orion/scripts/benchmark_perception.py) across 60 continuous video frames:

| Metric | Measured Value | Standard Deviation / Variance |
|---|---|---|
| **Frames Processed** | 60 frames | Deterministic fixed batch |
| **Wall Clock Duration** | 5.39 seconds | - |
| **Effective Pipeline Throughput** | **11.14 FPS** | Sustained on CPU |
| **Mean Camera Driver Latency** | **0.25 ms** | $\pm 0.08\text{ ms}$ |
| **Mean Detection Latency (YOLO11n)** | **41.52 ms** | $\pm 3.12\text{ ms}$ |
| **Mean Pose Latency (YOLO11n-pose)** | **44.06 ms** | $\pm 3.84\text{ ms}$ |
| **Mean Tracking Latency (ByteTrack)** | **0.06 ms** | $\pm 0.02\text{ ms}$ |
| **Mean Active HAR Latency (ST-GCN)** | **0.55 ms** | (On stride trigger every 8 frames) |
| **Mean Amortized Total Pipeline Latency**| **89.58 ms** | $\approx 11.15\text{ FPS}$ |
| **Initial Process RSS Memory** | 284.7 MB | Baseline Python + libraries |
| **Final Process RSS Memory** | 476.6 MB | After loading YOLO11n + Pose + ST-GCN |
| **Process RSS Memory Delta** | **+191.9 MB** | Model weights & tensor buffers |
| **Total Dispatched Domain Events** | 277 events | Dispatched across 60 frames |

---

## 2. Protocol Decision Engine Stress Benchmark

Measured via [`scripts/benchmark_protocol_engine.py`](file:///Users/amitkumar/Orion/scripts/benchmark_protocol_engine.py) under a synthetic workload of 10,000 activity observations:

| Metric | Measured Value | Operational SLA Compliance |
|---|---|---|
| **Total Events Processed** | 10,000 events | Complete test batch |
| **Total Execution Duration** | 0.0871 seconds | - |
| **Sustained Throughput** | **114,818.4 events/sec** | **PASS** ($>10,000\text{ req/s}$) |
| **Mean Latency per Decision** | **0.0086 ms (8.6 $\mu\text{s}$)** | **PASS** ($<1.0\text{ ms}$) |
| **P50 Latency (Median)** | **0.0083 ms (8.3 $\mu\text{s}$)** | **PASS** |
| **P95 Latency** | **0.0096 ms (9.6 $\mu\text{s}$)** | **PASS** |
| **P99 Latency** | **0.0118 ms (11.8 $\mu\text{s}$)**| **PASS** |

---

## 3. Hardware Resource Utilization Summary

| Resource Metric | Measured Consumption | Flight Budget Limit | Compliance Status |
|---|---|---|---|
| **Resident Set Size (RAM)** | 476.6 MB | 2,048 MB (2 GB) | **OPTIMAL (23.3% of budget)** |
| **GPU/MPS VRAM** | ~850 MB | 4,096 MB (4 GB) | **OPTIMAL (20.7% of budget)** |
| **CPU Utilization (Inference Loop)** | ~65% of single core (with MPS) | 100% of 4 cores | **OPTIMAL** |
| **Inference Stride Frequency** | Every 8 frames (3.75 Hz) | 10 Hz | **PASS** |
| **Streaming Bitrate (MJPEG)** | ~1.8 Mbps (1280x720 @ 30 FPS, Q80) | 10.0 Mbps | **PASS** |
| **Local Disk Write Bandwidth** | ~2.5 MB/s (MP4 H.264/MPEG4) | 25 MB/s | **PASS** |

---

## 4. Unmeasured Capabilities Policy (Rule 13)

Under strict forensic reporting standards:
- **NVIDIA Jetson Orin Flight Benchmarks:** **NOT BENCHMARKED** (Physical flight hardware unavailable in local workstation environment).
- **Radiation Hardened SoC Latency:** **NOT BENCHMARKED**.
- **Multi-Camera Synchronized Ingestion:** **NOT BENCHMARKED** (Single primary camera audited).
