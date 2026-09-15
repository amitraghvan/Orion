# ORION — BAS AI Copilot (SIH26174)
# Phase 1.3 Architecture Specification: Temporal HAR & ST-GCN

## 1. System Overview

Phase 1.3 adds temporal action recognition on top of the hardened Phase 1.2 perception pipeline:

```
Camera Sensor / Video Replay
             │
             ▼
[OpenCVCameraDriver] ─── (Capture Worker Thread + Ring Buffer maxlen=2)
             │
             ▼
[YOLOEdgeDetector] ─── (YOLO11n, asyncio.Lock + to_thread)
             │
             ▼
[ByteTracker] ─── (Multi-class protection det.class_id == trk.class_id)
             │
             ▼
[YOLOPoseEstimator] ─── (YOLO11n-Pose, 17 keypoints, asyncio.Lock + to_thread)
             │
             ▼
[Hungarian Pose ↔ Track Association] ─── (scipy linear_sum_assignment)
             │
             ▼
     StructuredObservation
             │
             ▼
   [TemporalHARRuntime]
        ├── 1. Per-Track Temporal Buffer (deque maxlen=T, stride S)
        ├── 2. Microgravity-Motivated Normalizer (Root centering, trunk scale, velocity)
        ├── 3. ST-GCN PyTorch Model (Spatial Graph Conv + Temporal Conv)
        ├── 4. Temporal Prediction Smoother (Hysteresis debounce)
        ├── 5. Uncertainty Evaluator (NOMINAL, UNKNOWN, UNCERTAIN, WARMING_UP, DEGRADED)
        └── 6. Semantic Activity Event Translator (START | UPDATE | CHANGE | END)
             │
             ▼
     ActivityRecognized Event
             │
     ┌───────┴────────────────────────┐
     ▼                                ▼
[InMemoryEventBus]              [WebSocket Telemetry Broadcaster]
     │                                │
     ▼                                ▼
[EventPersistenceSubscriber]    [React Cockpit HUD Canvas]
     │
     ▼
[SQLite Storage (`events` table)]
```

---

## 2. Core Subsystems

### 2.1 Dedicated `TemporalHARRuntime`
To prevent bloating `PerceptionPipelineCoordinator`, temporal intelligence is encapsulated within `TemporalHARRuntime`.

Responsibilities:
- Maintain independent `TemporalFeatureBuffer` instances per tracked astronaut.
- Regulate classification triggers using configurable stride intervals.
- Execute PyTorch ST-GCN forward passes with threadpool offloading.
- Apply temporal smoothing to suppress frame-level classification noise.
- Evaluate epistemic uncertainty (emitting `UNKNOWN` or `UNCERTAIN` when evidence is ambiguous).
- Translate raw predictions into semantic events (`START`, `UPDATE`, `CHANGE`, `END`).
- Quarantining failures: Any internal exception inside `TemporalHARRuntime` is caught and logged, marking the subsystem `DEGRADED` without terminating the optical perception coordinator.

### 2.2 Canonical Microgravity-Motivated Normalization
Astronauts aboard the Bharatiya Antariksh Station (BAS) operate under microgravity, resulting in arbitrary 3D orientations relative to fixed glovebox cameras. The normalization baseline standardizes 2D skeletal poses:

1. **Canonical Image Mapping**: Coordinates normalized to $[-0.5, 0.5]$ relative to maximum frame dimension.
2. **Root Centering**: Translation-invariance achieved by subtracting mid-hip position $P_{\text{root}} = \frac{1}{2}(P_{\text{l\_hip}} + P_{\text{r\_hip}})$.
3. **Trunk Scale Normalization**: Scale-invariance achieved by dividing centered coordinates by trunk length $s = \|P_{\text{mid\_shoulder}} - P_{\text{root}}\|_2$ with protective $\epsilon = 10^{-4}$.
4. **Motion Velocities**: Temporal motion captured by first-order backward difference: $V_{i, t} = P_{\text{norm}, i, t} - P_{\text{norm}, i, t-1}$.
5. **Feature Packing**: Yields a tensor of shape $(C=4, T, V=17)$ containing $[x, y, v_x, v_y]$.

### 2.3 Semantic Activity Event Dispatch
Rather than emitting repetitive events on every stride, the runtime uses a semantic state machine:
- `START`: Activity initiated (sustained over debounce window).
- `UPDATE`: Periodic status confirmation (default: 1 Hz heartbeat).
- `CHANGE`: Direct transition between distinct activities.
- `END`: Activity concluded, transitioning to `idle` or `UNKNOWN`.
All events are published via `InMemoryEventBus` to SQLite audit persistence and WebSocket client feeds.
