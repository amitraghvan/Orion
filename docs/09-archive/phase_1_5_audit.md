# ORION Phase 1.5 — Forensic Repository Audit
**SIH26174 | Multimodal Human–Object Interaction Intelligence**  
**Date:** September 2026

---

## 1. Frozen Baseline Inventory

### Layer 1 — Perception (Phase 1.1 / 1.2)

| Component | File | Status | Evidence |
|---|---|---|---|
| Camera Driver | [`opencv_driver.py`](file:///Users/amitkumar/Orion/ai/src/orion_ai/camera/opencv_driver.py) | ✅ Working | Dedicated capture thread + bounded ring buffer |
| YOLO Detector | [`yolo_detector.py`](file:///Users/amitkumar/Orion/ai/src/orion_ai/detection/yolo_detector.py) | ✅ Working | `asyncio.Lock` + `to_thread`, warmup pass |
| ByteTracker | [`byte_tracker.py`](file:///Users/amitkumar/Orion/ai/src/orion_ai/tracking/byte_tracker.py) | ✅ Working | Multi-class IoU, strict class matching, velocity |
| Pose Estimator | [`yolo_pose.py`](file:///Users/amitkumar/Orion/ai/src/orion_ai/pose/yolo_pose.py) | ✅ Working | COCO 17-keypoint, `asyncio.Lock` |
| Pose ↔ Track Assoc. | [`coordinator.py`](file:///Users/amitkumar/Orion/ai/src/orion_ai/runtime/coordinator.py) L50-88 | ✅ Working | Hungarian matching |
| Pipeline Coordinator | [`coordinator.py`](file:///Users/amitkumar/Orion/ai/src/orion_ai/runtime/coordinator.py) | ✅ Working | 5-stage DAG |

### Layer 2 — Temporal AI (Phase 1.3)

| Component | File | Status |
|---|---|---|
| Temporal Buffer | [`buffer.py`](file:///Users/amitkumar/Orion/ai/src/orion_ai/activity/buffer.py) | ✅ Working |
| Skeleton Graph | [`graph.py`](file:///Users/amitkumar/Orion/ai/src/orion_ai/activity/stgcn/graph.py) | ✅ Working |
| Normalization | [`normalization.py`](file:///Users/amitkumar/Orion/ai/src/orion_ai/activity/stgcn/normalization.py) | ✅ Working |
| ST-GCN Model | [`model.py`](file:///Users/amitkumar/Orion/ai/src/orion_ai/activity/stgcn/model.py) | ✅ Working |
| ST-GCN Classifier | [`stgcn_classifier.py`](file:///Users/amitkumar/Orion/ai/src/orion_ai/activity/stgcn_classifier.py) | ✅ Working |
| Temporal Smoothing | [`smoothing.py`](file:///Users/amitkumar/Orion/ai/src/orion_ai/activity/smoothing.py) | ✅ Working |
| HAR Runtime | [`runtime.py`](file:///Users/amitkumar/Orion/ai/src/orion_ai/activity/runtime.py) | ✅ Working |

### Layer 3 — Protocol Intelligence (Phase 1.4)

| Component | File | Status |
|---|---|---|
| Protocol Loader | [`loader.py`](file:///Users/amitkumar/Orion/experiments/loader.py) | ✅ Working |
| Decision Engine | [`decision_engine.py`](file:///Users/amitkumar/Orion/backend/src/orion/protocol/decision_engine.py) | ✅ Working |
| State Machine | [`state_machine.py`](file:///Users/amitkumar/Orion/backend/src/orion/protocol/state_machine.py) | ✅ Working |
| Next-Step Engine | [`next_step_engine.py`](file:///Users/amitkumar/Orion/backend/src/orion/protocol/next_step_engine.py) | ✅ Working |
| Protocol Service | [`service.py`](file:///Users/amitkumar/Orion/backend/src/orion/protocol/service.py) | ✅ Working |

### Layer 4 — Presentation

| Component | File | Status |
|---|---|---|
| FastAPI app | [`app.py`](file:///Users/amitkumar/Orion/backend/src/orion/api/app.py) | ✅ Working |
| Experiments API | [`experiments.py`](file:///Users/amitkumar/Orion/backend/src/orion/api/routers/experiments.py) | ✅ Working |
| WebSocket | [`telemetry_ws.py`](file:///Users/amitkumar/Orion/backend/src/orion/api/routers/telemetry_ws.py) | ✅ Working |
| Cockpit HUD | [`App.tsx`](file:///Users/amitkumar/Orion/frontend/src/App.tsx) | ✅ Working |

---

## 2. Reusable Components for Phase 1.5

| # | Component | Reuse Strategy |
|---|---|---|
| 1 | `ByteTracker` | **Extend** — already multi-class. Can track objects natively. |
| 2 | `BoundingBox2D` | **Reuse directly** — standard bbox for hands and objects. |
| 3 | `DetectionTarget` | **Reuse** — supports class_id, class_name, confidence, box, track_id. |
| 4 | `StructuredObservation` | **Extend** — add hand/object/interaction/multimodal fields. |
| 5 | `PipelineMetrics` | **Extend** — add hand/object/interaction/fusion latency. |
| 6 | `ProtocolEvidence` | **Extend** — add optional multimodal evidence fields. |
| 7 | `_compute_bbox_iou` | **Extract** — duplicated in coordinator.py and byte_tracker.py. |
| 8 | YOLO model loading pattern | **Reuse** — same architecture for object detection. |
| 9 | `ModelMetadata` + `LocalModelWeightsLoader` | **Extend task literal** — add `"hand"`, `"object"`. |
| 10 | `EventBus` | **Reuse** — subscribe new HOI events. |
| 11 | Pose wrist keypoints (9, 10) | **Reuse** — COCO joints provide hand seed regions. |

---

## 3. Missing Components (P0–P3)

| # | Gap | Severity | Description |
|---|---|---|---|
| G1 | No hand perception pipeline | **P0** | No `hand/` package exists |
| G2 | No object-specific detection | **P0** | YOLO only detects persons (class 0) |
| G3 | No object tracking in coordinator | **P0** | ByteTracker exists but unused for objects |
| G4 | No person→hand association | **P0** | No wrist-to-hand linking code |
| G5 | No hand-object spatial association | **P0** | Interaction package is stubs only |
| G6 | No interaction state machine | **P0** | No temporal interaction lifecycle |
| G7 | No multimodal evidence schema | **P0** | ProtocolEvidence has no HOI fields |
| G8 | No multimodal fusion engine | **P0** | No code combining modalities |
| G9 | No evidence quality model | **P1** | No EvidenceQuality computation |
| G10 | No conflict handling | **P1** | No conflicting modality detection |
| G11 | Interaction stubs never implemented | **P1** | `InteractionDetectorInterface` raises NotImplementedError |
| G12 | No HOI events in event taxonomy | **P1** | events/schemas.py missing HOI events |
| G13 | bbox_iou duplicated | **P2** | Identical logic in coordinator.py and byte_tracker.py |
| G14 | No hand/object in HUD | **P2** | App.tsx has no HOI cards |
| G15 | ModelMetadata.task missing hand/object | **P2** | Literal only has detection/pose/activity/interaction/segmentation |
| G16 | No license audit | **P2** | No docs/phase_1_5_license_audit.md |
| G17 | No ROI configuration | **P3** | No configurable glovebox/workstation regions |

---

## 4. Existing Interaction Package

[`ai/src/orion_ai/interaction/`](file:///Users/amitkumar/Orion/ai/src/orion_ai/interaction):

- `schemas.py`: Has `SpatialRelation`, `InteractionTriplet`, `InteractionResult` — useful but missing hand identity, temporal state, confidence gating, evidence quality.
- `interfaces.py`: `InteractionDetectorInterface.infer_interactions()` raises `NotImplementedError`.
- `configs.py` / `registry.py`: Empty scaffolding.
- **No implementation file**.

**Decision:** Preserve useful schemas as base. Build Phase 1.5 multimodal HOI on top.

---

## 5. Quality Gates (Current Baseline)

| Gate | Status | Result |
|---|---|---|
| Pytest | ✅ | 83 passed / 5.57s |
| Ruff | ✅ | All passed |
| Mypy (src) | ✅ | 0 issues / 148 files |
| Frontend Build | ✅ | 1.24s / 0 errors |
| Protocol Benchmark | ✅ | 132,778.6 events/sec |

---

## 6. Performance Baseline

| Stage | Measured Latency |
|---|---|
| Detection (YOLO11n) | ~10-30ms |
| Tracking (ByteTrack) | <1ms |
| Pose (YOLO-Pose) | ~15-40ms |
| ST-GCN HAR | ~2-5ms |
| Protocol Decision | 0.0074ms |
| **End-to-end** | **~30-80ms (12-30 FPS)** |

Phase 1.5 budget: +15-30ms acceptable. Must maintain >10 FPS.
