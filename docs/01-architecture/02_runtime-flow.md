# ORION Runtime Flow & Execution Trace

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments (SIH26174)  
**Organization:** Indian Space Research Organisation (ISRO)  
**Date:** September 17, 2026  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. System Entry Points

| Execution Mode | Entry Point Command | Primary Implementation File | Description |
|---|---|---|---|
| **Production Desktop** | `./launch.sh` or `python run.py` | [`run.py`](file:///Users/amitkumar/Orion/run.py) → [`app/main.py`](file:///Users/amitkumar/Orion/app/main.py) | Full native PySide6 desktop assistant with live camera, AI, TTS, and local storage |
| **Live Camera Index** | `python run.py --camera <index>` | [`app/main.py`](file:///Users/amitkumar/Orion/app/main.py) | Launches desktop cockpit targeting a specific hardware camera device (e.g., `--camera 0`) |
| **Demo / Replay** | `python run.py --demo` | [`app/main.py`](file:///Users/amitkumar/Orion/app/main.py) | Offline demonstration mode looping `assets/sample_replay.mp4` |
| **Video File Override** | `python run.py --video <path.mp4>` | [`app/main.py`](file:///Users/amitkumar/Orion/app/main.py) | Runs full desktop cockpit on a specific pre-recorded BAS video |
| **Custom Protocol** | `python run.py --protocol <path.yaml>` | [`app/main.py`](file:///Users/amitkumar/Orion/app/main.py) | Preloads a specific BAS protocol specification |
| **Headless REST API** | `uvicorn backend.src.orion.api.app:app` | [`backend/src/orion/api/app.py`](file:///Users/amitkumar/Orion/backend/src/orion/api/app.py) | FastAPI service exposing REST and WebSocket telemetry endpoints |
| **Live Camera Smoke** | `python scripts/smoke_test_live_camera.py` | [`scripts/smoke_test_live_camera.py`](file:///Users/amitkumar/Orion/scripts/smoke_test_live_camera.py) | Hardware capture and perception verification on webcam device 0 |
| **Replay Smoke Test** | `python scripts/smoke_test_replay.py` | [`scripts/smoke_test_replay.py`](file:///Users/amitkumar/Orion/scripts/smoke_test_replay.py) | Perception and FSM protocol progression on sample video |
| **Perception Benchmark** | `python scripts/benchmark_perception.py` | [`scripts/benchmark_perception.py`](file:///Users/amitkumar/Orion/scripts/benchmark_perception.py) | Measures FPS, latency, and memory for detection, pose, tracking, and HAR |
| **Protocol Benchmark** | `python scripts/benchmark_protocol_engine.py` | [`scripts/benchmark_protocol_engine.py`](file:///Users/amitkumar/Orion/scripts/benchmark_protocol_engine.py) | Measures decision engine throughput and microsecond latency |
| **HAR Training** | `python scripts/train_bas_har.py` | [`scripts/train_bas_har.py`](file:///Users/amitkumar/Orion/scripts/train_bas_har.py) | Fine-tunes ST-GCN on `datasets/bas_experiment/` kinematic sequences |
| **HAR Evaluation** | `python scripts/evaluate_bas_har.py` | [`scripts/evaluate_bas_har.py`](file:///Users/amitkumar/Orion/scripts/evaluate_bas_har.py) | Computes confusion matrix and per-class accuracy |
| **System Diagnostics** | `python scripts/doctor.py` | [`scripts/doctor.py`](file:///Users/amitkumar/Orion/scripts/doctor.py) | 7-point health check verifying Python, packages, DB, and architecture |

---

## 2. End-to-End Runtime Execution Flow

When ORION launches (`python run.py`), execution proceeds sequentially through the following 10 phases:

```
[Phase 1] System Startup
   │
   ▼
[Phase 2] Database Initialized (SQLite Alembic Schema 8cd806dc7e3d)
   │
   ▼
[Phase 3] Offline Audio TTS Initialized (macOS 'say' / Linux pyttsx3)
   │
   ▼
[Phase 4] AI Perception Models Loaded (YOLO11n, YOLO11n-pose, ST-GCN)
   │
   ▼
[Phase 5] Experiment Protocol Loaded (YAML specification)
   │
   ▼
[Phase 6] PySide6 GUI Created (MainWindow + Dashboard HUD)
   │
   ▼
[Phase 7] CameraManager Configured & Started (Dedicated Capture Thread)
   │
   ▼
[Phase 8] Decoupled InferenceConsumerWorker Commenced
   │
   ▼
[Phase 9] Optional IP Streaming Server Commenced (HTTP MJPEG 127.0.0.1:8080)
   │
   ▼
[Phase 10] Qt Main Application Event Loop (qt_app.exec())
```

---

## 3. Frame Processing Cycle (Decoupled Capture & Inference)

Every frame ingested into ORION traverses two decoupled threads:

### Thread 1: Camera Capture Worker (`LiveCameraSource` / `CameraManager`)
```
Hardware Camera Device (e.g. index 0)
   │
   ▼
cap.read() → cv2.Mat (BGR format, 1280x720)
   │
   ▼
FrameBuffer.put() (Ring buffer with maxlen=2, drops oldest unread frame)
   │
   ▼
actual_fps calculated via monotonic sliding window
```

### Thread 2: Inference Consumer Worker (`app/application.py`)
```
FrameBuffer.get_latest()
   │
   ├──► Check frame_id != last_processed_frame_id (Skip duplicates)
   │
   ▼
[Stage 1] Object Detection
   │      ultralytics.YOLO.predict(frame_bgr)
   │      Extract bboxes, class_ids, confidences for persons and experiment objects
   ▼
[Stage 2] Object Tracking
   │      ByteTracker.update(raw_detections)
   │      Assign persistent track_ids via Kalman filter and IoU
   ▼
[Stage 3] Pose Estimation
   │      YOLO11n-pose.predict(frame_bgr)
   │      Extract 17 COCO joints (x, y, confidence) per human subject
   ▼
[Stage 4] Hand Perception & HOI
   │      Extract left/right hand boxes from wrist (joints 9, 10) & elbow (joints 7, 8)
   │      Calculate Euclidean distance & IoU between hands and objects
   │      Transition ContactState (IDLE → APPROACH → TOUCH → MANIPULATE → RELEASE)
   ▼
[Stage 5] Temporal HAR Buffer
   │      Push 17-keypoint normalized coordinates into 32-frame sliding buffer
   │      Trigger ST-GCN forward pass on stride (every 8 frames)
   │      Compute Softmax probabilities across 8 action classes
   ▼
[Stage 6] Uncertainty Calibration
   │      Compute Shannon entropy H = -sum(p * log(p))
   │      Gate decision if confidence < min_conf (0.65) or entropy > max_entropy (1.40)
   ▼
[Stage 7] Protocol State Machine Evaluation
   │      ProtocolDecisionEngine.evaluate(observed_action, confidence, entropy)
   │      Debounce streak check (count >= 2)
   │      Match against current step expected actions
   │      Check for WRONG_OBJECT or OUT_OF_SEQUENCE violations
   ▼
[Stage 8] Output Routing & Dispatch
   ├──► Step Progression: Advance FSM step index if VALID
   ├──► Next Step Guidance: Compute upcoming instruction text
   ├──► Voice Synthesis: TTSEngine.speak() enqueues audio alert
   ├──► Structured Logging: StorageManager writes metadata.json & events.json
   ├──► Session Recording: ExperimentRecorder writes MP4 frame
   ├──► IP Streaming: StreamManager encodes frame as JPEG for MJPEG clients
   └──► Qt GUI Dispatch: FrameDispatcher emits Signal to main thread for HUD overlay
```
