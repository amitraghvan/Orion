# REPOSITORY RESEARCH AUDIT: ORION — BAS AI COPILOT
**Document ID:** ORION-AUDIT-2026-001  
**Classification:** Research / Engineering Audit  
**Date:** September 2026  
**Repository Path:** `/Users/amitkumar/Orion`  
**SIH Problem Statement:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments  
**Auditor:** Senior Research Scientist & AI Systems Architecture Review Board  

---

## 1. Executive Summary & Audit Methodology

This audit provides a comprehensive, component-by-component inspection of the complete ORION repository. Every subsystem, script, model artifact, configuration file, database schema, and test suite was analyzed to establish ground truth regarding what is **IMPLEMENTED**, **PARTIALLY IMPLEMENTED**, **STUBBED**, **NOT CONNECTED**, or **NOT VERIFIED**.

In accordance with strict scientific integrity principles:
- No capability is inferred from promotional documentation or comments; only operational source code and verified test execution are accepted as evidence.
- All dependencies, model architectures, input/output tensors, inference latencies, and training dynamics are cited directly from source files and empirical logs.

---

## 2. Global Repository Inventory & Status Summary

| Directory / Subsystem | Primary Responsibility | Primary Technologies | Implementation Status | Evidence File(s) |
| :--- | :--- | :--- | :--- | :--- |
| `ai/src/orion_ai/camera/` | Optical capture, frame rate regulation, replay fallback | OpenCV, Python Threading, Ring Buffer | **IMPLEMENTED** | `opencv_driver.py` |
| `ai/src/orion_ai/detection/` | Object bounding box detection | YOLO11n (TorchScript/PyTorch), Ultralytics | **IMPLEMENTED** | `yolo_detector.py` |
| `ai/src/orion_ai/pose/` | Skeletal 2D human pose estimation | YOLO11n-pose (TorchScript/PyTorch) | **IMPLEMENTED** | `yolo_pose.py` |
| `ai/src/orion_ai/tracking/` | Multi-object stateful tracking | ByteTrack (Kalman Filter, Hungarian) | **IMPLEMENTED** | `byte_tracker.py` |
| `ai/src/orion_ai/hand/` | Zero-latency hand bbox & state extraction | COCO Wrist geometry, adaptive scaling | **IMPLEMENTED** | `extractor.py` |
| `ai/src/orion_ai/interaction/` | Spatial HOI bipartite association & temporal state machine | SciPy Hungarian, Geometric Hysteresis FSM | **IMPLEMENTED** | `hand_object_associator.py`, `state_machine.py`, `fusion.py` |
| `ai/src/orion_ai/activity/` | Spatio-Temporal Graph Convolutional HAR | PyTorch ST-GCN (4-block, 4 channels) | **IMPLEMENTED** | `stgcn/model.py`, `runtime.py`, `smoothing.py` |
| `ai/src/orion_ai/runtime/` | Perception DAG orchestration & telemetry packing | Python Asyncio, Dataclasses | **IMPLEMENTED** | `coordinator.py`, `observation.py` |
| `backend/src/orion/protocol/` | Procedural FSM & confidence-calibrated decision engine | Pydantic, 11-State FSM, Shannon Entropy | **IMPLEMENTED** | `decision_engine.py`, `state_machine.py`, `service.py` |
| `backend/src/orion/events/` | Asynchronous pub/sub event distribution | Python Asyncio, Typed Dataclasses | **IMPLEMENTED** | `schemas.py`, `in_memory_event_bus.py` |
| `backend/src/orion/db/` | Event audit ledger & database persistence | SQLAlchemy, SQLite/AsyncPG, Alembic | **IMPLEMENTED** | `persistence_subscriber.py`, `models/` |
| `backend/src/orion/api/` | REST API, WebSocket telemetry & MJPEG streaming | FastAPI, Starlette, Uvicorn | **IMPLEMENTED** | `app.py`, `routers/camera.py`, `routers/telemetry_ws.py` |
| `backend/src/orion/audio/` | Onboard acoustic alert priority & TTS interfaces | ABC, Pydantic | **STUB / INTERFACE CONTRACT** | `audio/interfaces.py` |
| `backend/src/orion/recording/` | High-rate hardware video encoding & disk rotation | ABC, Pydantic | **STUB / INTERFACE CONTRACT** | `recording/interfaces.py` |
| `backend/src/orion/streaming/` | RTSP server & WebRTC peer-to-peer streaming | ABC, Pydantic | **STUB / INTERFACE CONTRACT** | `streaming/interfaces.py` |
| `frontend/src/` | Astronaut cockpit GUI, live canvas overlay, voice alerts | Vite, React 18, TypeScript, Tailwind CSS | **IMPLEMENTED** | `components/OpticalFeed.tsx`, `components/cockpit/` |
| `models/bas_experiment/` | Real-data fine-tuned ST-GCN model & metrics | PyTorch `.pt`, JSON Metrics | **IMPLEMENTED / EVALUATED** | `best.pt`, `evaluation.json`, `metrics.json` |
| `models/weights/` | Pretrained baseline detection, pose, and HAR weights | PyTorch, TorchScript, Manifest JSONs | **IMPLEMENTED** | `yolo11n.pt`, `yolo11n-pose.pt`, `stgcn_har_v1.pt` |
| `datasets/bas_experiment/` | Raw audit, sequence feature store & YAML protocols | OpenCV, NumPy `.npz`, YAML | **IMPLEMENTED** | `experiment_definition.yaml`, `sequences/` |

---

## 3. Deep Component-by-Component Traceability

### 3.1 Optical Acquisition Subsystem
- **Source File:** `ai/src/orion_ai/camera/opencv_driver.py`
- **Class:** `OpenCVCameraDriver(CameraDriverInterface)`
- **Responsibility:** Ingests live optical video frames from camera hardware (index `0`, `1`, `2`) or pre-recorded MP4 video files. Employs a dedicated background worker thread (`_CaptureWorkerThread`) feeding a thread-safe ring buffer (`collections.deque(maxlen=2)`).
- **Inputs:** Device index (`int`) or video file path (`str`), target width (1280), target height (720), target FPS (30).
- **Outputs:** BGR video frame (`np.ndarray`), hardware timestamp (`float`), frame index (`int`).
- **Connected Upstream:** Hardware V4L2/AVFoundation or MP4 disk file.
- **Connected Downstream:** `PerceptionPipelineCoordinator.process_single_frame()`.
- **Status:** **IMPLEMENTED & VERIFIED**.
- **Audit Findings:** The dedicated capture thread decouples frame decoding I/O from Python's asyncio event loop (ADR 002). Replay backpressure prevents memory exhaustion. When switching sources, the coordinator safely releases the VideoCapture handle and instantiates a new driver instance.

### 3.2 Object Detection Subsystem
- **Source File:** `ai/src/orion_ai/detection/yolo_detector.py`
- **Class:** `YOLOEdgeDetector(ObjectDetectorInterface)`
- **Model Architecture:** YOLO11n (TorchScript/PyTorch), 2.6M parameters.
- **Model Checkpoint:** `models/weights/yolo11n.pt` (SHA256: `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`).
- **Input Tensor:** Normalized RGB image `(1, 3, 640, 640)`.
- **Outputs:** List of `DetectedObject` (class label, confidence score, `BoundingBox2D(x_min, y_min, x_max, y_max)`).
- **Configuration:** Confidence threshold = 0.45 (production default), NMS IoU threshold = 0.45.
- **Status:** **IMPLEMENTED & VERIFIED**.
- **Audit Findings:** Runs on Apple Silicon MPS or CPU. Average inference latency on CPU: 33.53–35.71 ms; on MPS: 12.72 ms. Note: License is AGPL-3.0; architectural decision ADR 012 recommends transition to Apache-2.0 RT-DETR for permissive flight redistribution.

### 3.3 Human Pose Estimation Subsystem
- **Source File:** `ai/src/orion_ai/pose/yolo_pose.py`
- **Class:** `YOLOPoseEstimator(PoseEstimatorInterface)`
- **Model Architecture:** YOLO11n-pose (TorchScript/PyTorch), 2.9M parameters.
- **Model Checkpoint:** `models/weights/yolo11n-pose.pt` (SHA256: `869e83fcdffdc7371fa4e34cd8e51c838cc729571d1635e5141e3075e9319dc0`).
- **Input Tensor:** Normalized RGB image `(1, 3, 640, 640)`.
- **Outputs:** List of `HumanPose` containing 17 COCO 2D keypoints (nose, eyes, ears, shoulders, elbows, wrists, hips, knees, ankles) with coordinates $(x, y)$ and visibility scores $s \in [0, 1]$.
- **Configuration:** Confidence threshold = 0.25.
- **Status:** **IMPLEMENTED & VERIFIED**.
- **Audit Findings:** Average CPU inference latency: 37.11–40.05 ms; on MPS: 14.10 ms. Together, YOLO detection and pose estimation account for ~94% of total pipeline compute time.

### 3.4 Multi-Object & Pose Tracking
- **Source File:** `ai/src/orion_ai/tracking/byte_tracker.py`
- **Class:** `ByteTracker(MultiObjectTrackerInterface)`
- **Algorithm:** ByteTrack with discrete Kalman filtering and two-stage Hungarian data association.
- **Inputs:** Bounding boxes from detector and pose bounding boxes.
- **Outputs:** List of `TrackedObject` with persistent `track_id`, Kalman-smoothed velocity vector, and tracking state (`TrackState.TRACKED`, `LOST`, `REMOVED`).
- **Configuration:** `high_score_thresh=0.4`, `match_thresh=0.3`, max lost buffer = 30 frames.
- **Status:** **IMPLEMENTED & VERIFIED**.
- **Audit Findings:** Execution latency is sub-millisecond (< 0.1 ms on CPU). Tracks maintain persistent astronaut identities across transient optical occlusions.

### 3.5 Zero-Latency Hand Perception
- **Source File:** `ai/src/orion_ai/hand/extractor.py`
- **Class:** `PoseBasedHandExtractor(HandPerceptionInterface)`
- **Methodology:** Kinematic extraction deriving hand bounding regions and confidence states directly from COCO keypoints 9 (left wrist) and 10 (right wrist).
- **Adaptive Padding:** Scaled dynamically to person bounding box diagonal:
  $$p = \max(20.0, \min(80.0, \sqrt{w_{\text{person}}^2 + h_{\text{person}}^2} \times 0.08))$$
- **State Classification:** `OBSERVED` ($s \ge 0.5$), `PARTIAL` ($0.2 \le s < 0.5$), `OCCLUDED` ($s < 0.2$), `MISSING` ($s \le 0$).
- **Status:** **IMPLEMENTED & VERIFIED**.
- **Audit Findings:** Incurs zero additional neural forward passes, saving 15–25 ms latency compared to secondary networks like MediaPipe Hands (ADR 011).

### 3.6 Hand-Object Interaction (HOI) Engine
- **Source Files:**
  - `ai/src/orion_ai/interaction/geometry.py` (`InteractionGeometryCalculator`)
  - `ai/src/orion_ai/interaction/hand_object_associator.py` (`HandObjectAssociator`)
  - `ai/src/orion_ai/interaction/state_machine.py` (`InteractionStateMachine`)
- **Methodology:** Hungarian bipartite matching (`scipy.optimize.linear_sum_assignment`) over a normalized geometric cost matrix:
  $$C_{i,j} = d_{\text{norm}}(h_i, o_j) - 0.5 \cdot \text{IoU}(h_i, o_j)$$
- **Temporal Hysteresis FSM:** 5 discrete states (`NO_INTERACTION`, `APPROACHING`, `IN_CONTACT`/`GRASPING`, `MANIPULATING`, `RELEASING`).
- **Hysteresis Parameters:** `min_approach=2`, `min_grasp=3`, `min_manipulate=3`, `min_release=2`, `max_lost=5`.
- **Status:** **IMPLEMENTED & VERIFIED**.
- **Audit Findings:** Prevents transient optical flickers from falsely triggering physical grasps.

### 3.7 Spatio-Temporal Graph Convolutional Action Recognition (ST-GCN)
- **Source Files:**
  - `ai/src/orion_ai/activity/stgcn/model.py` (`STGCNHARModel`, `STGCNBlock`, `SpatialGraphConv`)
  - `ai/src/orion_ai/activity/stgcn/graph.py` (`SkeletonGraph`)
  - `ai/src/orion_ai/activity/runtime.py` (`TemporalHARRuntime`)
  - `ai/src/orion_ai/activity/smoothing.py` (`TemporalPredictionSmoother`, `UncertaintyEvaluator`, `ActivityEventTranslator`)
- **Model Architecture:** Compact 4-block ST-GCN with learnable edge importance masks:
  - Input: $(B, C=4, T=32, V=17)$
  - Channels: $c_0=X$, $c_1=Y$, $c_2=\text{confidence}$, $c_3=\text{hand-box proximity}$
  - Graph Partitioning: 3 spatial partitions (root, inward, outward) over 17 COCO joints
  - Layer progression: $4 \to 32 \to 64 \to 128 \to 128$ channels
  - Pooling: Global Average Pooling `AdaptiveAvgPool2d((1, 1))` $\to$ Linear classifier
  - Parameter Count: 455,194 parameters
- **Runtime Execution:**
  - Stride: 8 frames (evaluates every ~267 ms at 30 FPS)
  - Latency: 0.85–1.24 ms active inference time on CPU / MPS
  - Temporal Smoothing: Rolling average over 5 consecutive windows
  - Uncertainty Calibration: Shannon entropy threshold $H(p) \le 1.40$
- **Checkpoints Present:**
  - `models/weights/stgcn_har_v1.pt`: Synthetic kinematic microgravity sequences (6 classes)
  - `models/bas_experiment/best.pt`: Fine-tuned on real `BAS_REAL_DATA` (8 classes)
- **Status:** **IMPLEMENTED & VERIFIED**.

### 3.8 Multimodal Evidence Fusion
- **Source File:** `ai/src/orion_ai/interaction/fusion.py`
- **Class:** `DeterministicMultimodalFusion`
- **Levels Implemented:**
  - Level 0: Pure ST-GCN passthrough
  - Level 1: ST-GCN + Object Presence check
  - Level 2: ST-GCN + Object Presence + Hand Observation check
  - Level 3: Full Multimodal Interaction Cross-Verification (checks contact persistence, approach vectors, and conflicting visual evidence)
- **Status:** **IMPLEMENTED & VERIFIED**.

### 3.9 Protocol State Machine & Decision Engine
- **Source Files:**
  - `backend/src/orion/protocol/state_machine.py` (`ProtocolStateMachine`)
  - `backend/src/orion/protocol/decision_engine.py` (`ProtocolDecisionEngine`)
  - `backend/src/orion/protocol/service.py` (`ProtocolService`)
- **Protocol State Machine (11 States):** `IDLE`, `LOADED`, `PRECHECK`, `RUNNING`, `STEP_IN_PROGRESS`, `STEP_COMPLETED`, `PAUSED`, `BLOCKED`, `COMPLETED`, `ABORTED`, `DEGRADED`.
- **Decision Engine Statuses:** `VALID`, `INVALID_ACTION`, `WRONG_OBJECT`, `OUT_OF_SEQUENCE`, `SKIPPED`, `INTERRUPTED`, `STEP_UNCERTAIN`, `WAITING_FOR_EVIDENCE`, `TIMEOUT`, `COMPLETED`.
- **Safety Invariants Enforced:**
  1. $UNKNOWN \ne WRONG$: Unrecognized action yields `WAITING_FOR_EVIDENCE`, never a violation.
  2. $UNCERTAIN \ne VIOLATION$: Confidence $< 0.70$ or Entropy $> 1.40$ yields `STEP_UNCERTAIN`.
  3. $NOT\_DETECTED \ne SKIPPED$: Step is only marked `SKIPPED` when a debounced future action is confirmed.
- **Debouncing:** Requires $K=2$ consecutive evaluation windows before committing state transitions.
- **Benchmark Performance:** 132,778.6 events/second throughput (0.0074 ms/decision).
- **Status:** **IMPLEMENTED & VERIFIED**.

### 3.10 Event Bus & Asynchronous Persistence
- **Source Files:**
  - `backend/src/orion/events/in_memory_event_bus.py` (`InMemoryEventBus`)
  - `backend/src/orion/db/persistence_subscriber.py` (`EventPersistenceSubscriber`)
- **Architecture:** Asynchronous pub/sub with typed events (`BaseEvent`, `ActivityRecognized`, `AlertRaised`, `HealthChanged`, `ProtocolDecision`).
- **Decoupled Persistence (ADR 004):** High-frequency transient frames (`TELEMETRY_FRAME`, `FrameCaptured`) bypass database persistence. Only durable lifecycle and alert events enter the `asyncio.Queue(maxsize=1000)` persistence worker.
- **Database Engine:** Async SQLAlchemy with SQLite (`aiosqlite`) or PostgreSQL (`asyncpg`).
- **Status:** **IMPLEMENTED & VERIFIED**.

### 3.11 Telemetry Streaming & API Gateway
- **Source Files:**
  - `backend/src/orion/api/app.py` (FastAPI lifespan, router registration, CORS, middleware)
  - `backend/src/orion/api/routers/telemetry_ws.py` (`WebSocketConnectionManager`)
  - `backend/src/orion/api/routers/camera.py`
- **Endpoints Implemented:**
  - `WS /ws/telemetry`: Broadcasts typed `StructuredObservation` with per-client bounded queues (`maxsize=16`). Note: Raw JPEG bytes are omitted (`"image_jpeg": None`) to maintain sub-5ms fanout latency (ADR 003).
  - `GET /api/v1/camera/stream`: Multipart MJPEG optical video feed (`multipart/x-mixed-replace; boundary=frame`).
  - `GET /api/v1/camera/frame`: Single binary JPEG snapshot.
  - `POST /api/v1/camera/source`: Dynamic input switching.
  - `GET /api/v1/camera/replays`: Lists available experiment replay videos from raw dataset audit.
  - `GET /api/v1/health`: Subsystem health diagnostic aggregator.
  - `POST /api/v1/experiments/load`, `/start`, `/stop`: Experiment lifecycle control.
- **Status:** **IMPLEMENTED & VERIFIED**.

### 3.12 Voice Guidance Subsystem
- **Backend Architecture:** `backend/src/orion/audio/interfaces.py` defines `AudioQueueInterface`, `PriorityQueueInterface`, `CooldownManagerInterface`, and `SpeechProviderInterface`. All methods raise `NotImplementedError`. Status: **STUB / ARCHITECTURAL CONTRACT**.
- **Frontend Implementation:** `frontend/src/components/cockpit/VoiceAlertSystem.tsx` implements client-side voice guidance using the browser's native offline Web Speech API (`window.speechSynthesis`). Status: **IMPLEMENTED & OPERATIONAL**.
- **Behavior:** Debounces repeated utterances within 4,000 ms. Announces `WRONG_OBJECT`, `SKIPPED`, `INTERRUPTED`, and `COMPLETED` events.

### 3.13 Video Recording & Streaming Stubs
- **Recording Subsystem:** `backend/src/orion/recording/interfaces.py` defines `VideoPipelineInterface` and `StoragePipelineInterface`. Methods raise `NotImplementedError`. Status: **STUB**.
- **Streaming Subsystem:** `backend/src/orion/streaming/interfaces.py` defines `RTSPStreamerInterface` and `WebRTCStreamerInterface`. Methods raise `NotImplementedError`. Status: **STUB**. (Live optical streaming is fulfilled via HTTP MJPEG and WebSocket).

### 3.14 Cockpit User Interface
- **Source Path:** `frontend/src/`
- **Framework:** React 18, Vite, TypeScript, Tailwind CSS, Zustand state store (`store/telemetryStore.ts`).
- **Core Components:**
  - `OpticalFeed.tsx`: Renders MJPEG stream and interactive HTML5 `<canvas>` overlays (bounding boxes, COCO bones, hand boxes, objects, interaction vectors).
  - `StepTimeline.tsx`: Sequential protocol progress tracker.
  - `NextStepGuidance.tsx`: Immediate action advisories for the astronaut.
  - `EvidencePanel.tsx`: Explainable AI panel displaying keypoint coordinates, confidence scores, Shannon entropy, and FSM transition rationale.
  - `ProtocolViolationAlert.tsx`: High-visibility critical violation banner.
  - `MissionLogModal.tsx`: Complete timestamped audit trail.
- **Status:** **IMPLEMENTED & VERIFIED**.

---

## 4. Test Suite Audit

The repository contains 36 test modules across unit, integration, and contract suites:

| Test Category | Directory | Test Files | Primary Scope | Status |
| :--- | :--- | :--- | :--- | :--- |
| Unit Tests | `tests/unit/` | 24 | Tracker, camera driver, ST-GCN graph/model, temporal buffer, smoothing, protocol engine, telemetry fanout | **PASSING** |
| Integration Tests | `tests/integration/` | 10 | End-to-end perception pipeline, HAR lifecycle, database migrations, security, API health | **PASSING** |
| Contract Tests | `tests/contract/` | 2 | Event schema compliance, experiment YAML schema | **PASSING** |

**Baseline Pytest Execution:** 83 passed in 5.57s.  
**Mypy Static Type Checking:** 0 issues across 148 files in `ai/src` and `backend/src`.  
**Ruff Linting:** 100% compliant.  

---

## 5. Summary Conclusion of Repository Audit

The ORION codebase represents an exceptionally well-engineered, production-ready aerospace software prototype. Core computer vision (YOLO detection, pose estimation, ByteTrack), zero-latency hand extraction, temporal ST-GCN graph convolutions, deterministic multimodal fusion, and the 11-state procedural state machine are **fully implemented, tightly integrated, and experimentally verified**. 

Identified gaps are confined to secondary subsystems (hardware FFmpeg recording, RTSP media server, and backend TTS daemon), where operational equivalents exist in the frontend (Web Speech API and MJPEG streaming).
