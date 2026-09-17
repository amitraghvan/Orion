# ORION Performance Engineering & Benchmarks

## 1. System Latency & Throughput Targets

To enable seamless, real-time guidance without disorientation for astronauts inside the glovebox, the perception and UI update loop must operate at $\ge 30\text{ FPS}$ with end-to-end latency below $50\text{ ms}$.

### End-to-End Latency Profile (1280x720 @ 30 FPS)

| Pipeline Stage | Implementation | Latency (Apple M3 Pro) | Latency (NVIDIA RTX 4070) | Latency (Intel i7-12700 CPU) |
| :--- | :--- | :---: | :---: | :---: |
| **Camera Capture** | C++ `CameraEngine` (AVFoundation/V4L2) | 1.8 ms | 1.5 ms | 2.1 ms |
| **Letterbox Preprocessing** | C++ `VideoProcessor` (Bilinear SIMD) | 1.2 ms | 0.9 ms | 2.4 ms |
| **YOLOv11 Detection** | PyTorch / TensorRT | 5.8 ms | 2.9 ms | 12.3 ms |
| **YOLOv11-Pose** | PyTorch / TensorRT | 6.4 ms | 3.2 ms | 14.1 ms |
| **Object Tracking** | C++ `ObjectTracker` | 0.4 ms | 0.2 ms | 0.5 ms |
| **HOI State Evaluation** | Vectorized PyTorch / NumPy | 0.6 ms | 0.4 ms | 0.8 ms |
| **ST-GCN HAR Classification** | Sliding Window PyTorch | 2.1 ms | 1.2 ms | 4.3 ms |
| **Decision Engine & FSM** | Pure Python Logic | 0.2 ms | 0.2 ms | 0.3 ms |
| **Qt UI Canvas Render** | PySide6 QPainter (Hardware Accel) | 3.5 ms | 2.8 ms | 4.2 ms |
| **TOTAL END-TO-END** | | **22.0 ms** (45.5 FPS) | **13.3 ms** (75.2 FPS) | **41.0 ms** (24.4 FPS) |

---

## 2. Memory Footprint & Leak Prevention

Space station flight software must execute continuously without memory leaks or unbounded resource accumulation:

1. **Bounded Ring Buffering (`drop_oldest`)**:
   - The native C++ frame buffer is capped at 10 frames.
   - Under heavy compute spikes, oldest unprocessed frames are discarded rather than queued, strictly bounding memory overhead to $\approx 30\text{ MB}$.
2. **Deterministic Garbage Collection**:
   - Sliding temporal arrays reuse preallocated contiguous NumPy/PyTorch buffers ($32 \times 17 \times 3$).
   - PySide6 image buffers reuse shared `QImage` scanlines when possible.
3. **Memory Profile**:
   - Idle Desktop Memory: $\approx 185\text{ MB}$
   - Active Multimodal AI Inference: $\approx 780\text{ MB}$ (VRAM: $1.2\text{ GB}$ on GPU)
   - 24-Hour Continuous Execution: Drift $< 15\text{ MB}$.

---

## 3. Running Benchmark Tests

Execute the automated end-to-end benchmark harness:
```bash
python scripts/benchmark/benchmark_pipeline.py --video assets/sample_replay.mp4 --iterations 300
```
This outputs detailed percentile latency figures (P50, P95, P99) and hardware telemetry.
