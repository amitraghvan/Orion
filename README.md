# ORION: AI Human Activity Recognition for On-board BAS Experiments

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![C++20](https://img.shields.io/badge/C%2B%2B-20%20Native-00599C?style=flat-square&logo=c%2B%2B&logoColor=white)]()
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt%206-41CD52?style=flat-square&logo=qt&logoColor=white)](https://www.qt.io/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x%20MPS%2FCUDA%2FCPU-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![Air-Gapped](https://img.shields.io/badge/Operation-100%25%20Offline%20Air--Gapped-success?style=flat-square)]()
[![SIH26174](https://img.shields.io/badge/SIH26174-ISRO%20BAS%20Glovebox-blueviolet?style=flat-square)]()
[![Test Suite](https://img.shields.io/badge/Tests-205%20Passed%20(100%25)-brightgreen?style=flat-square)]()

---

## Overview

**ORION** is an offline, standalone, edge-native AI Copilot engineered to monitor, recognize, and validate human activities during scientific experiments aboard the **Bharatiya Antariksh Station (BAS)**. 

Designed under aerospace safety principles, ORION eliminates cloud dependencies, processing local camera feeds entirely at the edge to track experiment execution, detect sequence anomalies, provide prospective next-step guidance, issue offline voice alerts, and produce lightweight structured mission logs.

---

## SIH26174 Problem Statement

- **Organization:** Indian Space Research Organisation (ISRO)
- **Problem Statement ID:** SIH26174
- **Title:** AI Human Activity Recognition for On-board BAS Experiments
- **Theme:** Space Technology
- **Core Challenge:** Design and train an AI system that recognizes and validates the sequence of a predefined experiment using human activity recognition. The system must work as an offline standalone system and process local camera feeds at the edge.

---

## What ORION Does

1. **Ingests Continuous Video:** Captures video at native hardware rates (30 FPS) via a dedicated capture thread into a bounded ring buffer (`maxlen=2`), preventing latency build-up.
2. **Tracks Human & Object Motion:** Uses YOLO11n object detection, YOLO11n-pose (17 COCO joints), and ByteTrack multi-class tracking with Kalman velocity filtering.
3. **Analyzes Hand-Object Interaction (HOI):** Kinematically extracts astronaut hands from upper-limb joints and evaluates physical contact states (`APPROACH`, `TOUCH`, `MANIPULATE`, `RELEASE`) using spatial proximity and bounding box IoU.
4. **Recognizes Procedural Activities:** Passes 32-frame sliding skeletal windows (stride 8) through a Spatial-Temporal Graph Convolutional Network (**ST-GCN**).
5. **Validates Experiment Sequences:** Employs a formal 11-state Finite State Machine (FSM) to detect **skipped steps**, **out-of-sequence steps**, and **wrong-object manipulations**.
6. **Guides the Astronaut:** Synthesizes prospective next-step instructions visually on the HUD and vocally via speech.
7. **Issues Offline Voice Alerts:** Synthesizes spoken voice alerts via local OS speech utilities with priority preemption and anti-spam cooldown.
8. **Generates Structured Logs:** Records append-only SQLite records, machine-readable `events.json`, and human-readable `timeline.log`.
9. **Records Sessions Locally:** Asynchronously compresses video sessions to MP4 format without stalling perception.
10. **Streams Video over IP:** Hosts an independent HTTP multipart/x-mixed-replace MJPEG stream on port 8080 (`http://127.0.0.1:8080/live`).
11. **Provides Graphical Cockpit:** Features a native PySide6 (Qt) desktop application engineered with an aerospace dark cockpit theme (`#030712`), transparent corner brackets (`┌ ┐ └ ┘`), zero casual emojis, dynamic procedural guidance cards, and 10 dedicated telemetry views.

---

## Key Capabilities

- **100% Offline Air-Gapped:** Zero external network calls, zero telemetry, zero cloud APIs.
- **Hardware Acceleration:** Native support for Apple Silicon MPS (Metal Performance Shaders), NVIDIA CUDA, and multi-core CPU SIMD.
- **Decoupled Architecture:** Camera ingestion, AI inference, audio synthesis, disk recording, and GUI rendering run on independent threads.
- **Microgravity Invariant:** Torso-centered, scale-normalized skeletal coordinates provide robustness against zero-gravity body tilts and inversions.
- **Safe State Transitions:** Shannon entropy gating ($H \le 1.40$) and temporal debouncing prevent single-frame spurious spikes from advancing the protocol.

---

## System Architecture

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
└───────────┘└─────────┘└───────────┘  └──────────────────────────────┘
                                                      │
                                                      ▼
                                       ┌──────────────────────────────┐
                                       │  HTTP MJPEG Stream Server    │
                                       │  http://127.0.0.1:8080/live  │
                                       └──────────────────────────────┘
```

---

## AI Pipeline

```
[1. Camera (30 FPS)] ──► [2. FrameBuffer (maxlen=2)]
                                  │
                                  ▼
       ┌──────────────────────────┴──────────────────────────┐
       ▼                                                     ▼
[3. YOLO11n Object Detection]                 [4. YOLO11n-pose 17 Joints]
       │                                                     │
       ▼                                                     ▼
[5. ByteTrack Multi-Class]                    [6. Hand Kinematic Extractor]
       │                                                     │
       └──────────────────────────┬──────────────────────────┘
                                  ▼
                    [7. HOI Contact State Machine]
                                  │
                                  ▼
                    [8. 32-Frame Skeletal Buffer]
                                  │
                                  ▼
                    [9. ST-GCN Temporal Graph Convolutions]
                                  │
                                  ▼
                    [10. Entropy Gating & Debouncing]
                                  │
                                  ▼
                    [11. Protocol Decision Engine]
                                  │
                                  ▼
                    [12. Canonical Event Bus Dispatch]
```

---

## Experiment Workflow (Example: BAS-E01-A)

1. **Step 1:** Astronaut retrieves Yellow container from workstation. (Observed: `pick_yellow`, Expected: `pick_yellow`). $\to$ **VALID** $\to$ FSM advances to Step 2.
2. **Step 2:** Astronaut positions Yellow container into inspection zone. (Observed: `place_yellow`). $\to$ **VALID** $\to$ FSM advances to Step 3.
3. **Step 3:** Astronaut retrieves Red container. If astronaut retrieves Blue or manipulates out-of-order $\to$ **OUT_OF_SEQUENCE** or **WRONG_OBJECT** violation event emitted with immediate vocal alert.
4. **Step 4:** Astronaut positions Red container and finalizes sequence. $\to$ **COMPLETED** $\to$ Session finalized and structured report written.

---

## Technology Stack

- **Application & AI:** Python 3.11.14
- **Performance C++ Engine:** C++20 with pybind11 native bindings (`orion_native`)
- **Computer Vision:** OpenCV 4.10, NumPy 1.26
- **Deep Learning Models:** PyTorch 2.x, Ultralytics YOLO11n, YOLO11n-pose, ST-GCN
- **Hardware Acceleration:** Apple Silicon MPS, NVIDIA CUDA, CPU SIMD
- **Desktop UI:** PySide6 (Qt 6.8+ for Python)
- **Headless Backend:** FastAPI, Uvicorn, Starlette
- **Database & Persistence:** SQLite 3, SQLAlchemy 2.0 (async), Alembic
- **Speech Synthesis:** macOS `/usr/bin/say`, Linux `pyttsx3` / `espeak-ng`

---

## Repository Structure

```
Orion/
├── ai/                     # Computer vision pipeline, ST-GCN, and tracking
├── app/                    # Native PySide6 desktop GUI and coordinators
├── backend/                # Headless FastAPI services, DB models, and event bus
├── cpp/                    # High-performance C++20 engine with pybind11
├── configs/                # YAML configuration files for experiments and cameras
├── data/                   # Local SQLite databases (orion_dev.db) and migrations
├── datasets/               # BAS experiment datasets and sequence annotations
├── deployment/             # Deployment configurations, systemd units, Docker
├── docs/                   # Comprehensive forensic documentation hierarchy
│   ├── AUDIT_REPORT.md     # Master forensic audit report
│   ├── repository-map.md   # File-by-file repository breakdown
│   ├── architecture/       # System diagrams, runtime flows, and FSM specs
│   ├── ai/                 # Model inventory, dataset audit, and ST-GCN math
│   ├── compliance/         # SIH26174 compliance and traceability matrices
│   ├── deployment/         # Installation, air-gap, and configuration guides
│   ├── testing/            # Test strategy and empirical verification logs
│   ├── performance/        # Empirical latency and throughput benchmarks
│   ├── security/           # Threat model and vulnerability audit
│   └── research/           # Literature review, gaps, and research paper
├── models/                 # Neural network weights (.pt) and JSON manifests
├── recordings/             # Timestamped experiment session recordings & logs
├── scripts/                # CLI entry points, smoke tests, and benchmarks
└── tests/                  # Pytest test suites (unit, integration, python)
```

---

## Installation

### Prerequisites
- macOS 14+ (Apple Silicon / Intel) or Linux Ubuntu 22.04 LTS
- Python 3.11 installed
- `uv` (recommended) or standard `pip`

### Step-by-Step Setup
```bash
# 1. Clone repository
git clone https://github.com/amitraghvan/Orion.git
cd Orion

# 2. Set up virtual environment
uv venv .venv --python 3.11
source .venv/bin/activate

# 3. Install dependencies
uv pip install -r requirements.txt
uv pip install -r requirements-dev.txt

# 4. Verify system readiness
python scripts/doctor.py
```

Expected output:
```
📊 DOCTOR READINESS SCORE: 100.0% (7/7 checks passed)
🎉 Phase 0 Foundation is nominal and ready for development!
```

---

## Configuration

Settings are managed via [`configs/settings.yaml`](file:///Users/amitkumar/Orion/configs/settings.yaml) and overridable via environment variables:

```bash
export ORION_CAMERA_SOURCE="0"        # Camera device index or video file path
export ORION_MODELS_DEVICE="auto"     # "mps", "cuda", or "cpu"
export ORION_STREAMING_ENABLED="true" # Enable IP video streaming on port 8080
export ORION_AUDIO_VOICE_ENABLED="true" # Enable offline voice alerts
```

---

## Running ORION

### Primary Desktop Application
```bash
# Launch native Qt desktop cockpit
./launch.sh
# or directly:
python run.py
```

### Demonstration Mode (Video Loop)
```bash
# Launch in offline demo mode using sample replay video
python run.py --demo
```

### Video File Override
```bash
# Run against a specific pre-recorded BAS experiment video
python run.py --video assets/sample_replay.mp4
```

### Headless REST & Telemetry API
```bash
# Run headless backend server
uvicorn backend.src.orion.api.app:app --host 127.0.0.1 --port 8000
```

---

## Running Smoke Tests

### Live Camera Smoke Test
Verifies local webcam hardware capture, MPS acceleration, detection, pose, and event dispatch:
```bash
python scripts/smoke_test_live_camera.py
```
*Empirical Result:* 37 frames captured, 36 processed, 0 failures, **21.2 FPS**, **49.6 ms mean latency**.

### Replay Video Smoke Test
Verifies video replay through perception and protocol FSM:
```bash
python scripts/smoke_test_replay.py
```
*Empirical Result:* 30 frames processed, **21.3 FPS**, FSM state RUNNING, passed nominal.

---

## Dataset

- **Location:** `datasets/bas_experiment/`
- **Audit File:** `datasets/bas_experiment/reports/raw_data_audit.json`
- **Total Videos:** 20 video recordings (17 valid, 3 anomaly sequences: `Interruption`, `Wrong Object`, `Wrong Order`).
- **Subjects:** 4 human operators (`SP01`–`SP04`).
- **Protocols:** 5 spaceflight experiments (E01–E05).
- **Format:** 4K UHD and FHD HEVC (H.265) video.

---

## Model Inventory

| Model | Task | Path | Size | Parameters | Status |
|---|---|---|---|---|---|
| **YOLO11n** | Object Detection | `models/weights/yolo11n.pt` | 5.61 MB | ~2.6M | Real Pretrained Model |
| **YOLO11n-pose** | Pose Estimation | `models/weights/yolo11n-pose.pt` | 6.25 MB | ~2.9M | Real Pretrained Model |
| **ST-GCN Baseline**| Temporal HAR | `models/weights/stgcn_har_v1.pt` | 1.87 MB | 455,194 | Real Trained Baseline |
| **BAS Fine-Tuned** | BAS Experiment HAR | `models/bas_experiment/best.pt` | 1.86 MB | 455,194 | Real Fine-Tuned Model |

*Training Finding:* The fine-tuned ST-GCN model reaches **95.56% training accuracy**, but validation accuracy is **24.78%** on held-out subjects due to small dataset size (20 videos). Dataset scaling to 200+ videos is planned.

---

## Offline Operation

ORION is **100% air-gapped**:
- Zero outbound calls to cloud LLMs (OpenAI, Gemini, Groq).
- Zero cloud speech calls (ElevenLabs, Google Cloud TTS).
- Zero telemetry or analytics pings.
- All model weights and configs are loaded locally from disk.

---

## Video Recording

Experiment video is saved asynchronously to:
```
recordings/YYYY-MM-DD/<experiment_id>_<run_id>/
├── experiment.mp4         # Local MP4 video recording
├── metadata.json          # Mission timestamps and operator info
├── events.json            # Machine-readable JSONL event log
└── timeline.log           # Human-readable procedural timeline
```

---

## IP Streaming

When enabled, ORION serves a standard multipart MJPEG stream over HTTP:
- **URL:** `http://127.0.0.1:8080/live`
- **Codec:** Multipart JPEG (Quality 80)
- **Latency:** 30–60 ms over local network
- **Compatibility:** Viewable directly in any standard browser or VLC media player without external plugins.

---

## GUI

The native PySide6 desktop interface is engineered with an aerospace dark cockpit aesthetic (`#030712`), high-contrast tactical HUD accents, transparent corner reticles (`┌ ┐ └ ┘`), and strictly scientific telemetry indicators (`[NOMINAL]`, `[STANDBY]`, `[ACTIVE]`, `● LIVE`). It provides 10 dedicated cockpit views:
1. **Mission Dashboard:** Live camera HUD with transparent annotations, active step guidance cards, live subsystem indicators (`● SUBJECT`, `● SEQUENCE`, `● AUDIO`), and system metrics.
2. **Live View:** High-resolution expanded camera viewport with annotation toggles.
3. **Experiment View:** Interactive step-by-step checklist and sequence progression.
4. **Activity View:** Real-time temporal action confidence curves and entropy charts.
5. **Recordings View:** Historical mission session playback catalog.
6. **Reports View:** Markdown and PDF post-mission dossier generator.
7. **Dataset View:** Catalog of ground truth training sequences.
8. **Model View:** Checkpoint inspector and parameter audit.
9. **Diagnostics View:** 13-subsystem real-time health telemetry.
10. **Settings View:** Interactive camera, audio, and network configuration.

---

## Testing

Run the full automated test suite:
```bash
pytest tests/
```
**Results:** **205 passed, 0 failed** in 27.41 seconds (100% green).

Benchmark scripts:
```bash
# Perception latency benchmark
python scripts/benchmark_perception.py

# Protocol decision engine benchmark
python scripts/benchmark_protocol_engine.py
```

---

## Performance (Empirically Measured)

| Subsystem | Measurement | Device |
|---|---|---|
| **End-to-End Latency** | **49.60 ms (21.2 FPS)** | Apple Silicon MPS |
| **CPU End-to-End Latency** | **89.58 ms (11.14 FPS)** | Intel/Apple CPU |
| **ST-GCN HAR Forward Pass** | **0.55 ms** | CPU |
| **Protocol Decision Latency** | **0.0086 ms (114,818 events/sec)** | CPU |
| **Resident Memory (RSS)** | **476.6 MB** | Flat (Zero memory leak) |

---

## Limitations

1. **Dataset Volume:** The initial dataset contains 20 video recordings. While sufficient for architectural validation, dataset expansion to 200+ samples across diverse subjects is required for flight certification.
2. **3D Human Mesh Recovery:** Currently employs 2D torso-normalization for microgravity orientation invariance. True 3D SMPL mesh estimation is modeled in research but pending edge VRAM optimization.
3. **Custom Object Detection:** YOLO11n currently uses COCO classes; custom fine-tuning on specific flight apparatus is recommended.

---

## Current Implementation Status

- **Camera Subsystem:** **IMPLEMENTED** (Decoupled capture, ring buffer `maxlen=2`)
- **Object Detection:** **IMPLEMENTED** (YOLO11n, 80 classes)
- **Pose Estimation:** **IMPLEMENTED** (YOLO11n-pose, 17 joints)
- **Object Tracking:** **IMPLEMENTED** (ByteTrack multi-class)
- **Hand Perception & HOI:** **IMPLEMENTED** (Kinematic extraction, contact FSM)
- **Temporal HAR:** **IMPLEMENTED** (ST-GCN, 32-frame window, 8 classes)
- **Sequence Validation:** **IMPLEMENTED** (Protocol FSM, debounce, skip detection)
- **Next-Step Guidance:** **IMPLEMENTED** (HUD + Voice cues)
- **Offline Voice Alerts:** **IMPLEMENTED** (Priority queue, cooldown suppression)
- **Structured Logging:** **IMPLEMENTED** (SQLite + JSONL events)
- **Local Recording:** **IMPLEMENTED** (Asynchronous MP4 writer)
- **IP Streaming:** **IMPLEMENTED** (HTTP MJPEG port 8080)
- **Desktop GUI:** **IMPLEMENTED** (PySide6 10-view cockpit)
- **Offline Operation:** **IMPLEMENTED** (100% air-gapped, zero cloud calls)
- **BAS Dataset:** **PARTIAL** (20 real videos present, scaling needed)
- **3D HMR (Optional):** **PLANNED** (Research modeled)

---

## SIH Compliance

| Requirement | Capability | Status |
|---|---|---|
| R01 | Continuous local video processing | **PASS** |
| R02 | Experiment sequence tracking | **PASS** |
| R03 | Next-step guidance suggestion | **PASS** |
| R04 | Skipped step detection | **PASS** |
| R05 | Out-of-sequence step detection | **PASS** |
| R06 | Voice-based audio alerts | **PASS** |
| R07 | Timestamped structured logs | **PASS** |
| R08 | Outcomes and status | **PASS** |
| R09 | IP video streaming | **PASS** |
| R10 | Local video storage | **PASS** |
| R11 | Graphical monitoring UI | **PASS** |
| R12 | Offline standalone AI model | **PARTIAL** (Functional; dataset scaling needed) |
| R13 | Custom focused local dataset | **PARTIAL** (20 videos; expansion needed) |
| R14 | Multi-task CV (Det, Pose, HOI) | **PASS** |
| R15 | 3D Human Mesh Recovery (Opt) | **PLANNED** |

**Score:** **12 PASS**, **2 PARTIAL**, **1 PLANNED**, **0 BROKEN**.

---

## Research

Comprehensive research documents are located in [`docs/research/`](file:///Users/amitkumar/Orion/docs/research/):
- [`literature-review.md`](file:///Users/amitkumar/Orion/docs/research/literature-review.md): Survey across 22 scientific and aerospace domains.
- [`technical-research.md`](file:///Users/amitkumar/Orion/docs/research/technical-research.md): Deep learning model selection and HOI formulations.
- [`research-gaps.md`](file:///Users/amitkumar/Orion/docs/research/research-gaps.md): Forensic gap analysis on cross-subject generalization and occlusion.
- [`research-paper.md`](file:///Users/amitkumar/Orion/docs/research/research-paper.md): Full conference engineering research paper on hybrid neuro-symbolic architectures for spaceflight experiment assistance.

---

## Development Roadmap

- **Phase 1 (Completed):** Core perception, ST-GCN HAR, FSM sequence validator, offline voice alerts, desktop GUI, and decoupled camera driver.
- **Phase 2 (Near-Term):** Expand `BAS_REAL_DATA` to 200+ video recordings across varied astronaut anthropometries and lighting conditions.
- **Phase 3 (Mid-Term):** Fine-tune YOLO11n specifically on ISRO spaceflight glovebox apparatus (vials, clamps, incubation viewports).
- **Phase 4 (Long-Term):** Distill lightweight 3D Human Mesh Recovery (FastHMR) for full orientation invariance during zero-gravity translation.

---

## License

- **ORION Codebase:** Apache-2.0 License.
- **YOLO11 Models (Ultralytics):** AGPL-3.0 (Recommended flight alternative: RT-DETR Apache-2.0 or ONNX export).
- **PySide6 (Qt):** LGPL-3.0.
