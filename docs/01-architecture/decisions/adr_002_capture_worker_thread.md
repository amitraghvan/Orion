# Architectural Decision Record (ADR) 002: Dedicated Camera Capture Worker & Bounded Ring Buffer

## Status
**ACCEPTED** (2026-09-08)

## Context
High-rate video capture from optical sensors or hardware replay devices (such as OpenCV VideoCapture or GStreamer V4L2 pipelines) exhibits hardware-level I/O jitter, potential frame decode blocking, and buffer stalls. Executing `cap.read()` directly on Python's primary `asyncio` event loop blocks event dispatch, telemetry streaming, and user interactions. Conversely, scheduling raw `to_thread(cap.read)` on each frame poll introduces scheduling latency, unbounded internal OS camera driver buffer queues, and stale frame accumulation when perception model inference latency exceeds the optical camera frame interval.

## Decision
1. Isolate camera frame acquisition to a dedicated, persistent daemon thread (`_CaptureWorkerThread`).
2. Implement a thread-safe bounded ring buffer using `collections.deque(maxlen=2)` protected by a threading Lock.
3. Automatically evict older unconsumed frames on incoming frame arrivals when downstream perception inference lags behind sensor rate, ensuring the pipeline always processes the freshest optical state.
4. Provide non-blocking frame retrieval from the async loop via `await asyncio.to_thread(_pop_latest_frame)`.
5. Implement transient drop recovery budget (`MAX_TRANSIENT_DROPS = 5`) and loop replay rewind for test fixtures and hardware simulations.

## Consequences
- **Positive**: Zero event loop blocking from camera I/O. Hardware driver buffer saturation is prevented. Downstream inference delays cannot cause unbounded memory growth or stale sensor lag.
- **Negative**: Adds thread synchronization overhead and drops intermediate frames under high system load (by design).
