# CRITICAL LIMITATIONS & FUTURE RESEARCH ROADMAP: ORION
**Document ID:** ORION-LIMIT-2026-012  
**Classification:** Research Critique & Engineering Roadmap  
**Date:** September 2026  
**Repository Path:** `/Users/amitkumar/Orion`  
**SIH Problem Statement:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments  

---

## 1. Scientific & Methodological Limitations

In accordance with strict academic integrity, this section details the concrete boundaries, constraints, and current failure modes of the ORION system.

### 1.1 Extreme Small-Sample Regime ($N=4$ Subjects)
- **Deficiency:** The raw experimental corpus (`BAS_REAL_DATA`) contains only 20 video recordings spanning 4 distinct human subjects (`SP01` to `SP04`) and 1 unassigned anomaly operator.
- **Scientific Impact:** In deep learning for computer vision, training on 2 individuals and testing on a 3rd unseen individual represents an extreme out-of-distribution challenge. Skeletal limb proportions, arm reach, wrist rotation angles, and motion cadences vary significantly between humans.
- **Observed Manifestation:** Pure ST-GCN action recognition collapses to **2.98% top-1 accuracy** on held-out subject `SP04`, exhibiting heavy class collapse towards `check_box` and `pick_red`. While ORION's multimodal FSM successfully overrides this failure (achieving 100% violation detection via spatial object grounding), the underlying neural kinematic classifier remains severely ungeneralized.

### 1.2 Monocular Fixed Viewpoint & Optical Occlusion
- **Deficiency:** All recordings are captured from a single monocular camera positioned at a fixed table angle.
- **Scientific Impact:** When an astronaut's torso or arms rotate away from the optical axis, hand and apparatus regions suffer severe self-occlusion. Although ByteTrack and the HOI hysteresis machine mitigate transient dropouts, prolonged occlusion (> 5 frames) degrades spatial association. True 3D spatial reasoning requires multi-view stereoscopic triangulation.

### 1.3 Terrestrial 1-g Environment vs. True Microgravity Dynamics
- **Deficiency:** The current dataset was recorded in a standard 1-g terrestrial laboratory.
- **Scientific Impact:** In the microgravity environment of the Bharatiya Antariksh Station:
  - Astronauts float freely or lock themselves into foot restraints, adopting non-standard postures (e.g. neutral body posture, horizontal or inverted orientations).
  - Unrestrained apparatus boxes and tools drift freely with 6-DoF inertia rather than resting statically on tables.
  - While ORION's 2D upper-limb kinematic and geometric proximity algorithms are mathematically invariant to global table orientation, empirical validation under microgravity remains unverified.

### 1.4 Temporal Interruption Thresholding Limitation
- **Deficiency:** In the dedicated anomaly evaluation (`evaluation.json`), the Interruption anomaly clip (`RAW_video_20260912_183146.mp4`) scored a **0.0% detection rate**.
- **Root Cause:** The `ProtocolDecisionEngine` enforces a static step timeout parameter. In this specific video recording, the operator paused execution and stepped away, but the clip terminated before the elapsed idle duration exceeded the required timeout threshold. Consequently, the system remained in `WAITING_FOR_EVIDENCE` and did not flag an `INTERRUPTED` violation.

### 1.5 Secondary Subsystem Stubs in Backend
- **Deficiency:**
  1. **Backend TTS Daemon (`backend/src/orion/audio/interfaces.py`):** The Python audio subsystem defines priority queues and cooldown managers, but all synthesis methods raise `NotImplementedError`. (Operational voice guidance is executed client-side via the browser's native Web Speech API).
  2. **Hardware Video Muxing (`backend/src/orion/recording/interfaces.py`):** Archival storage interfaces raise `NotImplementedError`.
  3. **RTSP / WebRTC Media Server (`backend/src/orion/streaming/interfaces.py`):** Dedicated streaming server interfaces raise `NotImplementedError`. (Live optical streaming is fulfilled via HTTP MJPEG and WebSocket).

### 1.6 Copyleft Software Licensing Constraints
- **Deficiency:** The perception DAG relies on YOLO11n and YOLO11n-pose from Ultralytics, which are licensed under **AGPL-3.0**.
- **Aerospace Impact:** AGPL-3.0 copyleft terms mandate complete source disclosure if distributed or interacted with over a network. While air-gapped onboard flight payloads can operate standalone, commercial or permissive space agency redistribution requires migrating to an Apache-2.0 or MIT-licensed detector (e.g. RT-DETR or RTMPose).

### 1.7 Absence of Target Flight Hardware Benchmarking
- **Deficiency:** Hardware profiling has been conducted exclusively on Apple Silicon M-Series processors (CPU and MPS).
- **Impact:** Target spaceflight embedded nodes (e.g. NVIDIA Jetson AGX Orin Industrial, Jetson Orin Nano 8GB, or Raspberry Pi 5 with Hailo-8 NPU) have not been physically benchmarked in hardware-in-the-loop (HIL) testbeds.

---

## 2. Future Research Roadmap

```
+-----------------------------------------------------------------------------------+
|                         PHASE 2 RESEARCH & FLIGHT ROADMAP                         |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|   1. KINEMATIC DATA AUGMENTATION & SYNTHETIC MICROGRAVITY                         |
|      - Synthetic 3D kinematic scaling (varying limb lengths +/- 20%)              |
|      - Temporal warping (simulating microgravity execution delays)                |
|      - BlenderProc synthetic dataset generation with microgravity floating physics|
|                                                                                   |
|   2. PERMISSIVE APACHE-2.0 PERCEPTION UPGRADE                                     |
|      - Transition from YOLO11 (AGPL-3.0) to RT-DETR-R18 (Apache-2.0)              |
|      - Transition from YOLO-Pose to RTMPose-m (Apache-2.0)                        |
|      - ONNX Runtime INT8 quantization for embedded aerospace nodes               |
|                                                                                   |
|   3. DYNAMIC PROCEDURAL TIMEOUT MODELING                                          |
|      - Replace static step timeouts with learned Gaussian process or GBDT priors  |
|      - Enable rapid interruption detection (< 3.0s idle threshold)                |
|                                                                                   |
|   4. MULTI-VIEW 3D SKELETAL RECONSTRUCTION                                        |
|      - Dual-camera epipolar geometry inside science glovebox                      |
|      - 3D skeletal keypoint lifting invariant to astronaut body pitch / roll     |
|                                                                                   |
|   5. HARDWARE-IN-THE-LOOP (HIL) FLIGHT TESTBED                                    |
|      - Physical deployment on NVIDIA Jetson AGX Orin Industrial                   |
|      - Thermal chamber testing under simulated vacuum / conductive cooling        |
|      - Parabolic flight (zero-g aircraft) validation campaign                     |
+-----------------------------------------------------------------------------------+
```

### Milestone Schedule:
1. **Milestone 2.1 (Q1 2027):** Permissive license re-platforming (RT-DETR + RTMPose in ONNX FP16/INT8).
2. **Milestone 2.2 (Q2 2027):** Synthetic microgravity dataset expansion ($N=50$ virtual subjects via BlenderProc).
3. **Milestone 2.3 (Q3 2027):** Physical deployment and thermal validation on NVIDIA Jetson AGX Orin.
4. **Milestone 2.4 (Q4 2027):** Microgravity parabolic flight campaign validating free-floating apparatus tracking.
