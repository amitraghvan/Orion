# ORION Comprehensive Test Strategy & Verification Plan

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments (SIH26174)  
**Organization:** Indian Space Research Organisation (ISRO)  
**Date:** September 17, 2026  
**Status:** IMPLEMENTED & EXECUTED (189/189 TESTS PASSING)  

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

| Test Suite | Directory | Test Files Count | Scope & Focus |
|---|---|---|---|
| **Unit Tests** | [`tests/unit/`](file:///Users/amitkumar/Orion/tests/unit/) | 28 files | ST-GCN graph topology, mathematical invariance, ByteTrack multi-class tracking, Kalman filtering, bounding box IoU, temporal smoothing, protocol loader, entropy calculation. |
| **Python Regression Tests** | [`tests/python/`](file:///Users/amitkumar/Orion/tests/python/) | 9 files | Authoritative camera subsystem, bounded ring buffer, FSM lifecycle, decision engine debouncing, canonical 16-event bus pub/sub, 13-subsystem health derivation, failure resilience, C++ pybind11 native module. |
| **Integration Tests** | [`tests/integration/`](file:///Users/amitkumar/Orion/tests/integration/) | 4 files | End-to-end perception pipeline, FastAPI lifespan startup/shutdown, WebSocket telemetry fanout, security endpoints. |
| **Contract Tests** | [`tests/contract/`](file:///Users/amitkumar/Orion/tests/contract/) | 2 files | Pydantic and OpenAPI schema validation for REST endpoints. |
| **Golden Tests** | [`tests/golden/`](file:///Users/amitkumar/Orion/tests/golden/) | 1 file | Regression tests comparing perception outputs against verified golden observations. |

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
