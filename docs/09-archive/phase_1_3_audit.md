# ORION — BAS AI Copilot (SIH26174)
# Phase 1.3 Forensic Architecture Re-Audit

**Audit Date**: 2026-09-08  
**Author**: Principal AI/ML & Edge Systems Architect  
**Scope**: Forensic assessment of the repository baseline following Phase 1.2 hardening and prior to Phase 1.3 Temporal HAR implementation.

---

## 1. Executive Summary

Phase 1.2 successfully established a frozen, hardened perception baseline:
- **Test Matrix**: 40/40 tests passing in 2.46s.
- **Static Typing**: `mypy` strict passing with 0 errors across 121 source files.
- **Linter**: `ruff` passing with 0 errors.
- **Frontend**: TypeScript production bundle compiled in 1.28s.
- **Perception Benchmark (60 frames, Apple Silicon CPU)**: 14.05 FPS, 71.12 ms mean latency (Camera: 0.09 ms, Detection: 33.53 ms, Pose: 37.11 ms, Tracking & Hungarian Matching: 0.05 ms), RSS delta: +216.8 MB.

This forensic audit investigates all components required to support Phase 1.3 (Temporal HAR + ST-GCN), identifying existing assets, runtime gaps, failure modes, and classified priorities.

---

## 2. Component-by-Component Audit

### A. Camera & Frame Ingestion (`ai/src/orion_ai/camera/`)
- **Current State**: `OpenCVCameraDriver` runs a dedicated background capture thread (`_CaptureWorkerThread`) feeding a thread-safe ring buffer (`collections.deque(maxlen=2)`). Replay flow-control backpressure pauses disk reads when the buffer is full, preventing frame index runaway.
- **Audit Finding**: Camera driver is robust, thread-safe, and achieves 0.09 ms frame pop latency.
- **Phase 1.3 Need**: No changes needed; camera driver fulfills all temporal ingestion requirements.

### B. Object Detection (`ai/src/orion_ai/detection/`)
- **Current State**: `YOLOEdgeDetector` wraps YOLO11n weights with `asyncio.Lock()` inference serialization and `asyncio.to_thread` execution.
- **Audit Finding**: Latency is stable at 33.53 ms on CPU. Does not block the asyncio event loop.
- **Phase 1.3 Need**: Detection targets (e.g. tools, reagents) provide spatial context for future Human-Object Interaction (HOI) extension points.

### C. Multi-Object Tracking (`ai/src/orion_ai/tracking/`)
- **Current State**: `ByteTracker` enforces strict class matching (`det.class_id == trk.class_id`) in Pass 1 and Pass 2. Exposes `get_person_tracks()`.
- **Audit Finding**: Eliminates cross-class track hijacking. Generates temporally persistent `track_id` integers across consecutive frames.
- **Phase 1.3 Need**: Temporal HAR buffer must be keyed by `track_id` to maintain independent temporal sequences per astronaut.

### D. Human Pose Estimation (`ai/src/orion_ai/pose/`)
- **Current State**: `YOLOPoseEstimator` extracts 17-point whole-body COCO topological skeletons (`nose` through `right_ankle`) with `asyncio.Lock()` and `asyncio.to_thread`.
- **Audit Finding**: Latency is stable at 37.11 ms on CPU.
- **Phase 1.3 Need**: Skeletons serve as the primary geometric input to the ST-GCN graph.

### E. Hungarian Pose ↔ Track Association (`ai/src/orion_ai/runtime/coordinator.py`)
- **Current State**: `_associate_poses_with_tracks` solves bipartite matching via `scipy.optimize.linear_sum_assignment` on $1.0 - \text{IoU}(\text{pose}.\text{bbox}, \text{track}.\text{box})$. Mutates `pose.person_id = track.track_id`.
- **Audit Finding**: Skeletons maintain temporal identity consistency across occlusions and motion.
- **Phase 1.3 Need**: Essential prerequisite for temporal action recognition.

### F. Activity Recognition Interfaces & Schemas (`ai/src/orion_ai/activity/`)
- **Current State**: Contains legacy stubs (`ActivityWindow`, `ActivityPrediction`, `ActivityClassifierInterface`, `ActivityRegistry`) from Phase 0 with no actual temporal implementation.
- **Gaps Identified**:
  1. `ActivityClassifierInterface.classify_window` accepts an untyped `list[Any]`.
  2. No temporal feature buffering or per-track queue exists.
  3. No ST-GCN neural network or graph definition exists.
  4. No microgravity normalization pipeline exists.
  5. `registry.yaml` lists an empty mock model entry (`bas-har-timesformer-v1`).
- **Phase 1.3 Need**: Complete replacement with typed contracts, `TemporalFeatureBuffer`, `MicrogravityNormalizer`, PyTorch `STGCNHARModel`, and `TemporalHARRuntime`.

### G. Event Bus & Persistence (`backend/src/orion/`)
- **Current State**: `InMemoryEventBus` provides sub-millisecond in-process pub/sub. `EventPersistenceSubscriber` queues events for SQLite writes.
- **Audit Finding**: Phase 1.2 decoupled high-frequency frames from SQLite. `ActivityRecognized` is already classified as a durable domain event in `app.py`.
- **Phase 1.3 Need**: Semantic rate-controlled emission of `ActivityRecognized` events with `phase = "START" | "UPDATE" | "CHANGE" | "END"`.

### H. Telemetry WebSocket & HUD (`backend/src/orion/api/routers/telemetry_ws.py`, `frontend/`)
- **Current State**: `WebSocketConnectionManager` implements per-client bounded queues (`maxsize=16`) with drop-oldest for frames. Frontend Cockpit HUD renders detections, skeletons, and subsystem health.
- **Phase 1.3 Need**: Add HAR status tile to health matrix, add Action Recognition HUD overlay, and render action labels on canvas above tracked astronauts.

---

## 3. Classification of Findings & Priorities

| ID | Issue | Severity | Current State | Phase 1.3 Action |
|---|---|---|---|---|
| AUD-01 | No temporal feature buffer for sequence collection | **P0** | Missing | Implement `TemporalFeatureBuffer` with bounded deque, stride trigger, and stale track eviction |
| AUD-02 | No microgravity-motivated skeleton normalization | **P0** | Missing | Implement `MicrogravityNormalizer` with mid-hip root centering, trunk scale normalization, and velocity features |
| AUD-03 | No real ST-GCN neural network implementation | **P0** | Missing | Implement standalone PyTorch `STGCNHARModel` with spatial graph conv and temporal conv |
| AUD-04 | No trained HAR model weights or manifest | **P0** | Missing | Create offline training pipeline, train baseline, export `stgcn_har_v1.pt` and `stgcn_har_v1.manifest.json` |
| AUD-05 | No temporal decision smoothing or UNKNOWN evaluator | **P1** | Missing | Implement `TemporalPredictionSmoother` with hysteresis debounce and `UncertaintyEvaluator` |
| AUD-06 | No dedicated temporal runtime module | **P1** | Missing | Create `TemporalHARRuntime` to decouple temporal engine from coordinator orchestration |
| AUD-07 | ActivityRecognized event lacks semantic phase metadata | **P1** | Incomplete | Add `phase`, `track_id`, `model_version`, and `evidence_metadata` to event schema |
| AUD-08 | Frontend Cockpit HUD does not show HAR metrics or state | **P2** | Partial | Add HAR health indicator, Action Recognition HUD card, and canvas action labels |
| AUD-09 | 3D HMR / true 3D microgravity orientation invariance | **P3** | Future | Document as Phase 1.4+ research direction; use microgravity-motivated 2D baseline for Phase 1.3 |

---

## 4. Execution Roadmap

1. **Phase 1.3-A**: Forensic audit, change ledger, architecture docs, ADR 006 & ADR 007.
2. **Phase 1.3-B**: Typed temporal schemas and observation contracts.
3. **Phase 1.3-C**: `TemporalFeatureBuffer` with per-track bounded storage, stride regulation, and keypoint state tagging.
4. **Phase 1.3-D**: 17-keypoint skeletal graph and `MicrogravityNormalizer`.
5. **Phase 1.3-E**: PyTorch `STGCNHARModel` and `STGCNActivityClassifier` with deterministic inference test.
6. **Phase 1.3-F**: Offline dataset, controlled synthetic motion generator, training script, and model exporter.
7. **Phase 1.3-G**: `TemporalPredictionSmoother`, `UncertaintyEvaluator`, and `ActivityEventTranslator`.
8. **Phase 1.3-H**: `TemporalHARRuntime` and `PerceptionPipelineCoordinator` integration with fault isolation.
9. **Phase 1.3-I**: API, WebSocket fanout, health probe, and frontend cockpit HUD.
10. **Phase 1.3-J**: Regression testing, benchmark measurement, and long-run stability validation.
