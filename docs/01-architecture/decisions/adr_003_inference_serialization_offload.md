# Architectural Decision Record (ADR) 003: Model Inference Serialization & Non-Blocking Async Offload

## Status
**ACCEPTED** (2026-09-08)

## Context
Neural network forward passes (YOLO11 object detection and YOLO11-Pose skeleton estimation) are CPU/GPU-bound synchronous operations requiring 30–70 ms per frame on embedded edge hardware. Running PyTorch or ONNX Runtime inference directly inside `async def` functions blocks Python's single-threaded event loop, preventing heartbeat monitoring, WebSocket telemetry broadcasting, and health probe servicing. Furthermore, Ultralytics model instances maintain internal state and hardware execution buffers that are not thread-safe for concurrent forward passes.

## Decision
1. Serialize inference on each model wrapper (`YOLOEdgeDetector`, `YOLOPoseEstimator`) using an internal `asyncio.Lock()` per instance.
2. Offload heavy synchronous model forward passes (`self.model.predict(...)`) to worker threads via `await asyncio.to_thread(...)`.
3. Perform warm-up passes during initialization within worker threads to pre-allocate model buffers without halting application startup.

## Consequences
- **Positive**: The asyncio event loop remains fully responsive (handling REST requests, WebSocket frames, and health heartbeats in sub-millisecond time). Multiple concurrent callers to `detect()` or `estimate()` are safely serialized without race conditions or memory corruption.
- **Negative**: Adds negligible thread pool context-switching overhead (~0.1 ms per frame), vastly outweighed by eliminating 30–70 ms event loop stalls.
