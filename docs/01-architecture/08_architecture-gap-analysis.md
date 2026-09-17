# ORION Architecture Gap Analysis

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments (SIH26174)  
**Organization:** Indian Space Research Organisation (ISRO)  
**Date:** September 17, 2026  
**Status:** ARCHITECTURAL COMPARISON & FORENSIC AUDIT  

---

## 1. Current Architecture vs. Required Architecture

| Subsystem | Required Capability (SIH26174) | Current ORION Implementation | Architectural Assessment & Gap |
|---|---|---|---|
| **Camera Ingestion** | Continuous local video processing at edge | OpenCV capture thread + bounded ring buffer (`maxlen=2`) | **ALIGNED:** High throughput, decoupled, zero frame buildup |
| **Object Detection** | Detect experiment containers, tools, objects | YOLO11n (COCO 80 classes) | **PARTIAL GAP:** General COCO classes; needs fine-tuning specifically on flight glovebox tools |
| **Pose Estimation** | Extract astronaut bodily joint coordinates | YOLO11n-pose (17 COCO joints) | **ALIGNED:** 2D skeleton extraction functional on CPU and Apple Silicon MPS |
| **Tracking** | Maintain persistent human and object IDs | ByteTrack multi-class with Kalman filter | **ALIGNED:** Bipartite matching with class-aware track filtering |
| **Hand-Object Interaction** | Explicit HOI modeling & contact dynamics | Geometric wrist expansion + contact state machine | **ALIGNED:** Approach/Touch/Manipulate states derived from spatial distance & IoU |
| **Temporal HAR** | Classify procedural activities over time | ST-GCN on 32-frame sliding window (stride 8) | **ALIGNED BUT TRAINING GAP:** ST-GCN implemented, but validation accuracy on small dataset is 24.78% |
| **Sequence Validation** | Track sequence, detect skipped & out-of-order steps | Formal Protocol FSM + Decision Engine with debounce | **ALIGNED:** Explicit step rules, debouncing, lookahead skip detection |
| **Guidance System** | Suggest next step at start and after step | NextStepEngine calculating instructions | **ALIGNED:** Active and next step displayed on HUD and emitted via voice |
| **Voice Alerts** | Generate offline audio speech cues | Offline TTSEngine (macOS say / Linux pyttsx3/espeak) | **ALIGNED:** Zero cloud dependencies, priority queue, anti-spam cooldown |
| **Structured Logs** | Timestamped structured lightweight logs | SQLite database + JSONL `events.json` + `metadata.json` | **ALIGNED:** Fully compliant with flight data retention requirements |
| **Local Recording** | Store experiment video locally | Background OpenCV MP4 writer (mp4v/avc1) | **ALIGNED:** Asynchronous thread, date-partitioned session catalog |
| **IP Video Streaming** | Stream video to specified IP | HTTP multipart/x-mixed-replace MJPEG server | **ALIGNED:** Streamable over standard IP intranet on port 8080 |
| **Graphical UI** | Graphical monitoring interface | Native PySide6 Qt desktop cockpit with 10 views | **ALIGNED:** Mission dashboard, live video HUD, diagnostics, and reports |
| **Offline Operation** | Standalone offline edge system | 100% air-gapped, zero remote network calls | **ALIGNED:** Fully functional without internet connection |
| **Custom Dataset** | Focused dataset for BAS experiments | `datasets/bas_experiment/` (20 real videos) | **PARTIAL GAP:** Real dataset collected, but sample count (20 videos) is limited |
| **3D HMR (Optional)** | Orientation-agnostic 3D Human Mesh Recovery | 2D skeleton normalization used; 3D mesh pending | **PLANNED / RESEARCH GAP:** Optional requirement; documented in research papers |

---

## 2. Identified Architectural Risks & Technical Debt

1. **Model Generalization (Dataset Size):**
   - The ST-GCN temporal HAR model achieves 95.56% training accuracy, but validation accuracy is 24.78% on `BAS_REAL_DATA`. The dataset consists of 20 videos across 4 subjects. Expanding the dataset to 200+ samples across varied astronaut orientations is required for flight deployment.
2. **Object Detection Fine-Tuning:**
   - The system currently utilizes pretrained YOLO11n weights. While it detects `person` and generic objects accurately, dedicated custom annotations for BAS-specific apparatus (e.g., specific reaction chambers, microgravity pipettes) should be integrated.
3. **Optional 3D Human Mesh Recovery (HMR):**
   - SIH26174 lists 3D HMR as an optional capability. Currently, microgravity rotation invariance is achieved through 2D torso centering and coordinate scale normalization. True 3D SMPL mesh estimation requires significant additional edge VRAM.
