# ORION Native Desktop Architecture: Bharatiya Antariksh Station AI Copilot

## 1. System Overview

ORION is an air-gapped, high-reliability, offline native desktop AI copilot purpose-built for astronauts and payload specialists on-board the **Bharatiya Antariksh Station (BAS)** under ISRO SIH26174. 

The architecture completely eliminates browser and web server dependencies, unifying a **high-throughput C++20 vision engine** with an ergonomic **Qt 6 / PySide6 desktop GUI** and an intelligent multi-stage computer vision inference pipeline.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             ORION DESKTOP GUI                                │
│                     (PySide6 / Qt 6 - Mission Control Theme)                │
│                                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐ │
│  │ Dashboard    │ │ Live View    │ │ Protocol FSM │ │ Mission Reports    │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────────────┘ │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Qt Signals & Slots / Thread-Safe EventBus
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    PYTHON ORCHESTRATION & INFERENCE LAYER                    │
│                                                                             │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌────────────────────┐ │
│  │ Protocol FSM         │  │ Decision & Guidance  │  │ Audio / Offline    │ │
│  │ (11 Discrete States) │  │ (Entropy/Debouncing) │  │ TTS Annunciator    │ │
│  └──────────▲───────────┘  └──────────▲───────────┘  └────────────────────┘ │
│             │                         │                                     │
│  ┌──────────┴─────────────────────────┴───────────┐  ┌────────────────────┐ │
│  │ Multistage Perception Pipeline                 │  │ Local SQLite &     │ │
│  │ • YOLOv11 Detector & YOLOv11-Pose (COCO-17)    │  │ MP4 Video Logger   │ │
│  │ • Hand-Object Contact Engine (5 Discrete States)│ └────────────────────┘ │
│  │ • Fine-Tuned ST-GCN HAR (32-frame buffer)      │                         │
│  └──────────────────────────▲─────────────────────┘                         │
└─────────────────────────────┼───────────────────────────────────────────────┘
                              │ pybind11 Zero-Copy / Fast Memory Sharing
┌─────────────────────────────▼───────────────────────────────────────────────┐
│                      C++20 NATIVE HIGH-THROUGHPUT ENGINE                     │
│                             (orion_native.so/.pyd)                          │
│                                                                             │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌────────────────────┐ │
│  │ Video Capture Thread │  │ Bounded Ring Buffer  │  │ Video Processor    │ │
│  │ (OpenCV / V4L2 / AV) │  │ (drop_oldest policy) │  │ (SIMD Letterbox)   │ │
│  └──────────────────────┘  └──────────────────────┘  └────────────────────┘ │
│                                                                             │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌────────────────────┐ │
│  │ C++ ByteTracker      │  │ Video Recorder       │  │ MJPEG Stream Engine│ │
│  │ (Kalman + Hungarian) │  │ (H.264 / MP4V Sink)  │  │ (Local IP Bridge)  │ │
│  └──────────────────────┘  └──────────────────────┘  └────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Architectural Pillars

### 2.1 C++20 Native Engine (`cpp/`)
1. **Bounded Ring Buffer (`FrameBuffer`)**:
   - Fixed capacity (default: 10 frames) prevents memory growth and backpressure.
   - `drop_oldest` policy guarantees zero-latency, fresh frame processing under high computational loads.
   - Mutex-protected with condition variables for non-blocking producer-consumer decoupling.
2. **Video Processor (`VideoProcessor`)**:
   - Ultra-fast letterbox resizing with aspect ratio preservation and padding.
   - Bilinear interpolation and planar CHW tensor normalization ($[0.0, 1.0]$) in optimized C++.
3. **Native Object Tracker (`ObjectTracker`)**:
   - Real-time bounding box association using Intersection-over-Union (IoU) distance metrics and track state management (`TrackedBBox`).
4. **Recording & Streaming Engines**:
   - Background multi-threaded video encoding to disk.
   - Native HTTP MJPEG socket streamer for secondary ground or station diagnostic displays without touching application threads.

### 2.2 Python Intelligence & Inference Layer (`app/intelligence/`)
1. **Model Manager & Backends (`app/models/`)**:
   - Dynamic device targeting (`cuda`, `mps`, `cpu`).
   - Pluggable backends: PyTorch (`.pt`), ONNX Runtime (`.onnx`), and TensorRT (`.engine`).
2. **Keypoint & Hand-Object Interaction (`HOI`) Engine**:
   - COCO-17 human pose keypoint extraction via YOLOv11-Pose.
   - Hand bounding box projection from wrist and elbow joints with anatomically scaled margins.
   - Discrete 5-state interaction machine: `IDLE` $\to$ `APPROACH` $\to$ `TOUCH` $\to$ `MANIPULATE` $\to$ `RELEASE`.
3. **Spatio-Temporal Action Recognition (`TemporalEngine`)**:
   - Sliding 32-frame keypoint history buffer.
   - Spatial-Temporal Graph Convolutional Network (ST-GCN) evaluated over human skeleton topologies.
   - Softmax entropy calculation:
     $$H(p) = -\sum_{i=1}^C p_i \ln(p_i)$$
     Filters out spurious inferences when predictive uncertainty exceeds configurable thresholds ($H > 1.40$).
4. **Confidence Calibration & Debouncing (`DecisionEngine`)**:
   - Protocol invariant verification: checks expected action tokens against calibrated model outputs.
   - Temporal debouncing ($K \ge 2$ consecutive observations) prevents flickering and false positives.
   - Anomaly detection: classifies actions as `VALID`, `WRONG_OBJECT`, `OUT_OF_SEQUENCE`, or `INVALID_ACTION`.

### 2.3 11-State Protocol FSM (`app/experiments/sequence_manager.py`)
Deterministic execution lifecycle ensures complete traceability and safety:
1. `IDLE`: Initial ready state.
2. `LOADED`: Protocol YAML validated and cached with SHA-256 fingerprint.
3. `PRECHECK`: Hardware, camera sensors, and glovebox instruments verified.
4. `RUNNING`: Master mission timer initiated.
5. `STEP_IN_PROGRESS`: Real-time AI validation active for current step.
6. `STEP_COMPLETED`: Current procedural step satisfied.
7. `PAUSED`: Execution temporarily suspended by astronaut.
8. `BLOCKED`: Hazardous condition or out-of-sequence step requiring operator confirmation.
9. `COMPLETED`: All protocol steps nominal.
10. `ABORTED`: Emergency stop invoked.
11. `DEGRADED`: Hardware or sensor degradation; pure Python / fallback operational mode.

---

## 3. Native Desktop UI (`app/ui/`)

The user interface is designed according to aerospace "Mission Control" standards:
- **Telemetry Bar (Top)**: Station ID (`BAS-SCIENCE-NODE-1`), Glovebox ID (`GB-01`), FPS indicator, active AI backend (`PyTorch/MPS`), and UTC mission clock.
- **Navigation Sidebar (Left)**: Instant single-click switching between 10 specialized views.
- **Main View Area**:
  - `Dashboard`: High-level operational summary, camera feed preview, protocol overview, recent events.
  - `Live View`: Full-resolution video canvas with real-time bounding box, skeleton, and HOI overlays.
  - `Experiment View`: Interactive protocol execution interface with step progress, automated guidance, and manual overrides.
  - `Activity View`: Real-time action recognition classification probability bars and temporal entropy gauge.
  - `Recordings View`: Catalog of saved MP4 sessions with playback options.
  - `Reports View`: Scientific mission verification dossiers with markdown viewer and JSON inspection.
  - `Models View`: Loaded model status, backend selection, benchmark latencies, and device configuration.
  - `Dataset View`: Exploration of fine-tuned BAS HAR dataset classes, splits, and sample distribution.
  - `Diagnostics View`: Hardware resource utilization, memory graphs, and camera drop counters.
  - `Settings View`: System configuration, camera resolution, audio/TTS volume, and air-gap toggles.
- **Status Footer (Bottom)**: Active log sink, offline air-gap assurance badge, and notification marquee.
