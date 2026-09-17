# ORION System Architecture Overview

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments  
**Problem Statement:** SIH26174 | Indian Space Research Organisation (ISRO)  
**Date:** September 17, 2026  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. High-Level Architectural Diagram

The diagram below reflects the **actual verified runtime architecture** implemented across `app/`, `ai/src/orion_ai/`, and `backend/src/orion/`.

```
                      ┌────────────────────────────────────────┐
                      │          LOCAL VIDEO SOURCE            │
                      │  Live Webcam (CSI/USB) / Replay File   │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │             CameraManager              │
                      │  Singleton Driver & Ring FrameBuffer   │
                      │        (Bounded maxlen=2, ~30 FPS)     │
                      └─────────────┬──────────────────────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  │ (Zero-Copy Latest Frame Fetch)    │
                  ▼                                   ▼
   ┌──────────────────────────────┐    ┌──────────────────────────────┐
   │    InferenceConsumerWorker   │    │     FastAPI REST Router      │
   │    Decoupled Perception Thread│    │     /api/v1/camera/frame     │
   └──────────────┬───────────────┘    └──────────────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │                 IntelligenceEngine (ai/orion_ai)                 │
   │                                                                  │
   │   1. Object Detection (YOLO11n PyTorch/MPS/CPU)                  │
   │   2. Pose Estimation (YOLO11n-pose, 17 COCO Keypoints)           │
   │   3. Multi-Class Tracking (ByteTracker + Kalman Filter)          │
   │   4. Hand Extraction (Wrist/Elbow Geometric Expansion)          │
   │   5. Hand-Object Interaction (Proximity & Contact State Machine) │
   │   6. Temporal HAR (ST-GCN, 32-frame window, 8-frame stride)      │
   │   7. Uncertainty Calibration (Entropy & Moving Average)          │
   └──────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │             StructuredObservation & Event Bus                    │
   │             16 Canonical Pub/Sub Domain Events                   │
   └──────────────┬───────────────────────────────┬───────────────────┘
                  │                               │
                  ▼                               ▼
   ┌──────────────────────────────┐ ┌─────────────────────────────────┐
   │   Protocol Decision Engine   │ │     Qt GUI Frame Dispatcher     │
   │   & Protocol State Machine   │ │     Thread-safe Signal/Slot     │
   └──────────────┬───────────────┘ └─────────────────┬───────────────┘
                  │                                   │
      ┌───────────┼───────────┐                       ▼
      ▼           ▼           ▼        ┌──────────────────────────────┐
┌───────────┐┌─────────┐┌───────────┐  │     Native PySide6 GUI       │
│Next Step  ││Voice TTS││Storage &  │  │  Mission Dashboard & HUD     │
│Guidance   ││Engine   ││SQLite DB  │  │  Live Telemetry & Logs       │
│Engine     ││macOS/   ││recordings/│  └──────────────────────────────┘
│Next action││pyttsx3  ││events.json│                 ▲
└─────┬─────┘└────┬────┘└─────┬─────┘                 │
      │           │           │        ┌──────────────┴───────────────┐
      └───────────┴───────────┴───────►│  HTTP MJPEG Stream Server    │
                                       │  http://127.0.0.1:8080/live  │
                                       └──────────────────────────────┘
```

---

## 2. Core Architectural Subsystems

### 2.1 Authoritative Camera Subsystem (`ai/src/orion_ai/camera/`)
- **Design Pattern:** Singleton Camera Manager backed by a dedicated capture worker thread.
- **Hardware Decoupling:** Hardware capture operates at the camera's native rate (30 FPS) into a bounded ring buffer (`maxlen=2`). If downstream AI inference takes 45 ms (~22 FPS), the capture thread continuously overwrites the oldest unread frame, preventing latency build-up while preserving hardware synchronization.
- **Single Handle Protection:** Only one hardware `cv2.VideoCapture` instance is opened for the entire application. Native Qt GUI, background AI inference, and FastAPI HTTP preview endpoints all consume from the singleton manager, eliminating OS resource contention.

### 2.2 Deep Learning Perception Engine (`ai/src/orion_ai/`)
- **Object Detection:** Ultralytics YOLO11n loaded locally from `models/weights/yolo11n.pt`. Detects human subjects, tools, and experiment objects with bounding box coordinates, class IDs, and confidence scores.
- **Pose Estimation:** YOLO11n-pose loaded from `models/weights/yolo11n-pose.pt`. Extracts 17 COCO skeletal keypoints per human subject.
- **Multi-Class Tracking:** ByteTrack implementation maintaining persistent track IDs across frames using Kalman filtering and bipartite IoU matching.
- **Hand Perception:** Geometric wrist/elbow expansion deriving hand bounding boxes and centers for astronaut left and right hands.
- **Hand-Object Interaction (HOI):** Spatial evaluation assessing Euclidean distance and bounding box intersection over union (IoU) between hands and experiment objects, transitioned through a formal contact state machine (`APPROACH`, `TOUCH`, `MANIPULATE`, `RELEASE`).
- **Temporal HAR:** Spatial-Temporal Graph Convolutional Network (ST-GCN) processing sliding windows of 32 skeleton frames (8-frame stride). Classifies procedural astronaut actions.
- **Uncertainty Calibration:** Shannon entropy calculation gating out ambiguous predictions when entropy exceeds calibrated threshold ($H > 1.40$).

### 2.3 Protocol State Machine & Sequence Validator (`backend/src/orion/protocol/`)
- **Protocol Schema:** YAML experiment definitions specifying expected sequential steps, required actions, target objects, and confidence thresholds.
- **Sequence Invariants:** Evaluates each incoming HAR observation against the active step:
  - **VALID:** Action matches active step, confidence $\ge \tau$, entropy $\le H_{max}$, debouncing streak satisfied.
  - **OUT_OF_SEQUENCE:** Action belongs to a future step in the protocol, indicating an astronaut jumped ahead or skipped intermediate steps.
  - **WRONG_OBJECT:** Manipulated object contradicts protocol step object requirements (e.g., Red container instead of Yellow).
  - **INVALID_ACTION:** Unrecognized or prohibited procedural movement.
  - **STEP_UNCERTAIN:** Model confidence too low or entropy too high; observation deferred.

### 2.4 Event Bus & Subsystem Health (`backend/src/orion/events/`)
- **Event Bus:** Decoupled in-memory publish-subscribe architecture isolating subscriber exceptions.
- **16 Canonical Events:** Strict domain event taxonomy covering perception, protocol progression, voice synthesis, and video recording.
- **13 Subsystems Monitored:** Real-time health derivation covering camera, AI, detection, pose, hand, HOI, HAR, FSM, database, voice, recording, streaming, and compute acceleration.

### 2.5 Presentation & Monitoring (`app/ui/`)
- **PySide6 Native Cockpit:** High-frequency, air-gapped desktop GUI operating with sub-millisecond UI latency.
- **Zero-Copy Rendering:** Decoupled Qt signal/slot transfer displaying bounding boxes, skeletal joints, hand indicators, and interaction vectors directly overlaid on video.
- **Web Telemetry:** Secondary FastAPI REST API and WebSocket streaming telemetry for remote mission observation.
- **Network Streaming:** HTTP multipart/x-mixed-replace MJPEG server broadcasting live annotated video over IP.
