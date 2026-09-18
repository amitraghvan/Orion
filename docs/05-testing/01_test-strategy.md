# ORION Comprehensive Test Strategy & Verification Plan

---

## 1. Multi-Tiered Verification Strategy

ORION enforces a multi-tiered aerospace-aligned testing strategy (DO-178C software considerations in airborne systems):

```
                        ┌───────────────────────────────┐
                        │     System Smoke & Replay     │
                        │  Live Camera, Video Replay,   │
                        │     Benchmarks, Doctor CLI    │
                        └───────────────┬───────────────┘
                                        │
                        ┌───────────────▼───────────────┐
                        │       Integration Tests       │
                        │    End-to-End Perception,     │
                        │   FastAPI Lifespan, WebSocket │
                        └───────────────┬───────────────┘
                                        │
                        ┌───────────────▼───────────────┐
                        │      Contract & DB Tests      │
                        │   Alembic Migrations, SQLite, │
                        │      REST Endpoint Schemas    │
                        └───────────────┬───────────────┘
                                        │
                        ┌───────────────▼───────────────┐
                        │          Unit Tests           │
                        │  ST-GCN Graph, ByteTrack,     │
                        │  FSM, Decision Engine, HOI    │
                        └───────────────────────────────┘
```

---

## 2. Test Suite Architecture

| Test Suite | Directory | Files / Tests | Scope & Focus |
|---|---|---|---|
| **Unit Tests** | [`tests/unit/`](file:///Users/amitkumar/Orion/tests/unit/) | 29 files / 66 tests | ST-GCN graph topology, mathematical microgravity invariance, ByteTrack multi-class tracking, Kalman filtering, bounding box IoU, temporal smoothing, feature transforms, protocol loader, entropy calculation. |
| **Python Regression Tests** | [`tests/python/`](file:///Users/amitkumar/Orion/tests/python/) | 13 files / 44 tests | Authoritative camera subsystem, bounded ring buffer, FSM lifecycle, decision engine debouncing, canonical 16-event bus pub/sub, 13-subsystem health derivation, failure resilience, offline airgap verification, recording & reports runtime, C++ pybind11 native module. |
| **Integration Tests** | [`tests/integration/`](file:///Users/amitkumar/Orion/tests/integration/) | 8 files / 57 tests | End-to-end perception pipeline, FastAPI lifespan startup/shutdown, database migrations & sessions, runtime health contracts, security authentication, WebSocket telemetry fanout. |
| **Contract Tests** | [`tests/contract/`](file:///Users/amitkumar/Orion/tests/contract/) | 2 files / 3 tests | Pydantic and OpenAPI schema validation for domain events and experiment protocols. |
| **Golden Tests** | [`tests/golden/`](file:///Users/amitkumar/Orion/tests/golden/) | 2 files / 35 tests | Regression tests comparing perception and HOI outputs against verified golden observations and protocol scenarios. |
| **Total Test Suite** | [`tests/`](file:///Users/amitkumar/Orion/tests/) | **54 files / 205 tests** | **100% Passing (0 failures, 27.41s execution duration)** |

---

## 3. Dedicated Smoke & Benchmark Scripts

In addition to automated Pytest suites, 5 standalone verification scripts validate live hardware and performance:

1. **`scripts/smoke_test_live_camera.py`**:
   - Opens local webcam hardware (device 0).
   - Ingests frames at native hardware rate into bounded buffer.
   - Runs YOLO11n detection, YOLO-pose keypoints, and ST-GCN HAR with Apple Silicon MPS acceleration.
   - Verifies zero dropped frames and dispatches canonical domain events onto event bus.
2. **`scripts/smoke_test_replay.py`**:
   - Feeds a pre-recorded BAS experiment video (`assets/sample_replay.mp4`) through perception and protocol FSM.
   - Verifies step progression, decision logging, and clean shutdown.
3. **`scripts/benchmark_perception.py`**:
   - Benchmarks end-to-end perception pipeline over 60 frames.
   - Measures camera latency, detection latency, pose latency, tracking latency, HAR latency, effective FPS, and RSS memory growth.
4. **`scripts/benchmark_protocol_engine.py`**:
   - Stresses the protocol decision engine across 10,000 synthetic activity events.
   - Measures throughput in events/sec and P50/P95/P99 latency.
5. **`scripts/doctor.py`**:
   - 7-point health check verifying Python version, `uv`, Node/npm, monorepo layout, settings loading, SQLite engine, and host architecture.

---

## 4. Replay Scenario Verification Matrix

| Scenario Name | Stimulus Video / Observations | Expected FSM Decision | Expected Alert & Outcome |
|---|---|---|---|
| **Nominal In-Sequence** | Steps 1, 2, 3, 4 executed in prescribed order | `VALID` at each step | Step advances; next-step guidance updated; experiment completes. |
| **Out-of-Sequence** | Step 3 executed while Step 2 is active | `OUT_OF_SEQUENCE` | Immediate voice warning: *"Out of sequence activity detected"*; Step 2 flagged as skipped. |
| **Wrong Object** | Manipulating Red container during Yellow step | `WRONG_OBJECT` | Immediate voice warning: *"Warning. Wrong object manipulated"*; step remains on active step. |
| **Marginal / Low Confidence** | Model confidence 0.45 or entropy 1.60 | `STEP_UNCERTAIN` | Action suppressed; observation logged as uncertain; no false transition. |
| **Temporal Debouncing** | Single-frame spurious action spike | `WAITING_FOR_EVIDENCE` | Streak counter resets; state machine does not advance until action persists for 2 strides. |
