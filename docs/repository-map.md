# ORION Repository Map

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments  
**Problem Statement:** SIH26174 | Indian Space Research Organisation (ISRO)  
**Verification Date:** September 17, 2026  
**Status:** Authoritative Repository Map  

---

## 1. Top-Level Directory Structure

```
Orion/
├── ai/                     # AI/CV perception models, preprocessing, ST-GCN, HOI, and coordinator
├── app/                    # Native Qt (PySide6) desktop application and UI views
├── backend/                # Headless FastAPI services, DB models, event bus, and protocol engine
├── cpp/                    # High-performance C++20 engine with pybind11 Python bindings
├── configs/                # YAML configuration files for experiments, cameras, and runtime
├── data/                   # Local SQLite databases (orion_dev.db), migrations, and caches
├── datasets/               # BAS experiment datasets, video recordings, and sequence annotations
├── deployment/             # Deployment configurations, systemd units, Docker, and installer scripts
├── docs/                   # Comprehensive forensic architecture, AI, compliance, and research docs
├── experiments/            # Experiment protocol specifications and scenario definitions
├── infrastructure/         # Local infrastructure automation and system configurations
├── models/                 # Neural network weights (.pt) and JSON provenance manifests
├── recordings/             # Timestamped experiment session recordings and JSONL event logs
├── reports/                # Automated audit, evaluation, and test reports
├── scripts/                # CLI entry points, smoke tests, benchmarks, and training utilities
├── tests/                  # Pytest test suite (unit, integration, contract, golden, python)
└── tools/                  # Developer utilities and dataset tools
```

---

## 2. Component & Directory Detail

### 2.1 Native Desktop Application (`app/`)
- **Purpose:** Primary graphical monitoring interface (SIH26174 Req 11), desktop coordinator, and local mission controller.
- **Key Files:**
  - `run.py`: Universal desktop launcher adding root to `sys.path` and calling `app.main.main()`.
  - `app/main.py`: CLI parser supporting `--demo`, `--video`, `--camera`, and `--protocol`.
  - `app/application.py`: Master coordinator managing Qt loop, decoupled capture worker, background `InferenceConsumerWorker`, and graceful shutdown.
  - `app/camera/camera_manager.py`: Singleton `authoritative_camera_manager` managing camera lifecycle without hardware contention.
  - `app/intelligence/intelligence_engine.py`: Runs detection (YOLO11n), pose (YOLO11n-pose), tracking (ByteTrack), HOI, and ST-GCN HAR.
  - `app/experiments/experiment_engine.py`: Coordinates mission runs, evaluates observations, triggers step progression, and publishes voice/logging events.
  - `app/recording/recorder.py`: Asynchronous OpenCV MP4 session recorder writing to date-partitioned folders.
  - `app/streaming/stream_manager.py`: Standalone HTTP multipart/x-mixed-replace MJPEG video server (`http://127.0.0.1:8080/live`).
  - `app/audio/tts_engine.py`: Threaded offline text-to-speech synthesizer supporting macOS `say` and Linux `pyttsx3`/`espeak`.
  - `app/ui/main_window.py`: PySide6 QMainWindow containing navigation, status bar, and 10 tabbed cockpit views.
  - `app/ui/dashboard.py`: Mission dashboard showing live video HUD, active step guidance, audio status, and performance telemetry.

### 2.2 AI & Computer Vision Subsystem (`ai/src/orion_ai/`)
- **Purpose:** Standalone, air-gapped perception engine executing detection, tracking, pose estimation, hand-object interaction, and temporal HAR.
- **Key Modules:**
  - `camera/`: `LiveCameraSource`, `ReplayVideoSource`, `FrameBuffer` (bounded `maxlen=2`), and `CameraManager`.
  - `detection/`: `YOLOEdgeDetector` wrapping Ultralytics PyTorch/TorchScript YOLO11n.
  - `pose/`: `YOLOPoseEstimator` extracting 17 COCO body keypoints.
  - `tracking/`: `ByteTracker` providing multi-class association with Kalman filter velocities.
  - `hand/`: `HandExtractor` extracting wrists and bounding boxes from skeletal keypoints.
  - `interaction/`: `HandObjectInteractionEngine`, `SpatialRelation`, and contact state machine (`APPROACH`, `TOUCH`, `MANIPULATE`, `RELEASE`).
  - `activity/stgcn/`: Spatial-Temporal Graph Convolutional Network (`STGCNModel`, `Graph`, `SpatialGraphConv`).
  - `activity/stgcn_classifier.py`: Real-time sliding window classifier (32-frame buffer, 8-frame stride).
  - `activity/smoothing.py`: Exponential moving average and entropy-calibrated uncertainty evaluator.
  - `runtime/coordinator.py`: 5-stage async perception DAG orchestrating full pipeline.
  - `runtime/observation.py`: Canonical `StructuredObservation` schema.

### 2.3 Headless Backend & Event Bus (`backend/src/orion/`)
- **Purpose:** Headless FastAPI REST & WebSocket APIs, SQLite persistence layer, and decoupled in-memory pub/sub event bus.
- **Key Modules:**
  - `api/routers/camera.py`: Zero-contention camera status and frame endpoints consuming from `authoritative_camera_manager`.
  - `api/routers/health.py`: Truthful 13-subsystem health derivation (`camera`, `ai`, `detection`, `pose`, `hand`, `hoi`, `har`, `fsm`, `db`, `voice`, `recording`, `streaming`, `compute`).
  - `api/routers/experiments.py`: Experiment lifecycle management and step progression.
  - `api/routers/telemetry_ws.py`: High-throughput WebSocket broadcasting structured observation telemetry.
  - `events/event_bus.py`: Asynchronous in-memory `EventBus` with error isolation.
  - `events/schemas.py`: All 16 canonical domain events (`FrameCaptured`, `ObjectDetected`, `PoseDetected`, `HandDetected`, `InteractionDetected`, `ActionRecognized`, `StepStarted`, `StepCompleted`, `StepViolation`, `ExperimentStarted`, `ExperimentCompleted`, `ExperimentFailed`, `VoiceRequested`, `RecordingStarted`, `RecordingStopped`, `ObservationCaptured`).
  - `protocol/decision_engine.py`: Protocol decision engine evaluating entropy, confidence, debouncing, and out-of-order steps.
  - `protocol/state_machine.py`: Formal FSM tracking experiment states (`IDLE`, `ARMED`, `RUNNING`, `STEP_IN_PROGRESS`, `PAUSED`, `ABORTED`, `FAILED`, `COMPLETED`).
  - `db/`: SQLAlchemy async ORM models, Alembic migrations (`8cd806dc7e3d`), and SQLite persistence.

### 2.4 High-Performance C++ Subsystem (`cpp/`)
- **Purpose:** Hardware acceleration routines, SIMD image preprocessing, and pybind11 native bindings (`orion_native`).
- **Key Files:**
  - `cpp/src/core/video_processor.cpp`: High-speed letterboxing, color conversions, and tensor packing.
  - `cpp/src/tracking/tracker.cpp`: C++ tracker implementation.
  - `cpp/src/bindings/pybind_module.cpp`: Python bindings exposing `orion_native` module.
  - `CMakeLists.txt`: Build specification for native extensions.

### 2.5 Neural Network Models (`models/`)
- **`models/weights/yolo11n.pt`**: 5.61 MB. COCO 80-class detector. Real weights verified.
- **`models/weights/yolo11n-pose.pt`**: 6.25 MB. COCO 17-keypoint pose estimator. Real weights verified.
- **`models/weights/stgcn_har_v1.pt`**: 1.87 MB. 455,194 parameters. Pretrained ST-GCN baseline. Real weights verified.
- **`models/bas_experiment/best.pt`**: 1.86 MB. Fine-tuned ST-GCN on `BAS_REAL_DATA` with 8 action classes. Real weights verified.

### 2.6 Datasets & Experiment Definitions (`datasets/`, `experiments/`)
- **`datasets/bas_experiment/reports/raw_data_audit.json`**: Exhaustive catalog of 20 BAS experiment video recordings.
- **`datasets/bas_experiment/experiment_definition.yaml`**: Full specification of BAS experiment steps, actions, objects, and validation rules.
- **`configs/protocols/`**: Protocol YAML specifications (`bas_e01_a.yaml` through `bas_e05_b.yaml`).

### 2.7 Verification & Test Suites (`tests/`, `scripts/`)
- **`tests/python/`**: Dedicated regression test suite (camera subsystem, FSM, decision engine, 16 events, 13 health subsystems, failure handling, native module).
- **`tests/unit/`**: 70+ unit tests for ST-GCN graph topology, ByteTrack, bounding box IoU, temporal buffers, and smoothing.
- **`tests/integration/`**: End-to-end perception pipeline and FastAPI lifespan tests.
- **`tests/contract/`**: REST API schema contract tests.
- **`scripts/smoke_test_live_camera.py`**: Verifies real local webcam capture, MPS acceleration, detection, pose, and event dispatch.
- **`scripts/smoke_test_replay.py`**: Verifies recorded video replay through perception and protocol FSM.
- **`scripts/benchmark_perception.py`**: Latency and throughput benchmark for camera, YOLO, pose, tracking, and HAR.
- **`scripts/benchmark_protocol_engine.py`**: Evaluates protocol decision engine throughput and SLA latency.
- **`scripts/doctor.py`**: Comprehensive 7-point environment and monorepo diagnostics.
