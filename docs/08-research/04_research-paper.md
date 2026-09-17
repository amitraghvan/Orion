# A Hybrid Multimodal Architecture for Procedural Human Activity Recognition and Sequential Protocol Validation in Constrained Microgravity Experiments

**Engineering Research Paper | ORION Bharatiya Antariksh Station (BAS) AI Copilot**  
**Problem Statement:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments  
**Consortium:** Bharatiya Antariksh Station AI Systems Engineering Group | ISRO  
**Date:** September 17, 2026  

---

## Abstract

Human spaceflight experiments conducted onboard orbital platforms such as the upcoming Bharatiya Antariksh Station (BAS) require meticulous procedural adherence under extreme environmental, physiological, and cognitive constraints. While deep learning has significantly advanced computer vision and Human Activity Recognition (HAR), state-of-the-art models are conventionally evaluated on massive benchmarks ($N \ge 100$ subjects) and post-hoc video segmentation tasks. When deployed in small-sample aerospace domains ($N \le 4$), purely neural kinematic classifiers suffer catastrophic generalization collapse on unseen operators.

To overcome this fundamental limitation, we present **ORION**, an edge-native, neuro-symbolic AI copilot for real-time procedural experiment monitoring, next-step guidance, and violation detection. ORION integrates a lightweight visual perception Directed Acyclic Graph (DAG) (YOLO11n object detection, YOLO11n-pose estimation, and ByteTrack tracking), zero-latency kinematic hand extraction from upper-limb joints, a 4-channel Spatio-Temporal Graph Convolutional Network (ST-GCN) encoding hand-object proximity, and an 11-state deterministic procedural Finite State Machine (FSM).

We evaluate the system on `BAS_REAL_DATA`, a genuine 20-video experimental corpus capturing physical experiment executions across four human subjects and an anomaly suite under a strict zero-leakage subject-level split. Empirical results reveal that while a standalone ST-GCN achieves 95.56% training accuracy, its top-1 classification accuracy collapses to **24.78%** (Macro F1: **0.0146**) on a strictly held-out human subject (`SP04`) due to cross-subject morphological and viewpoint variance. However, when embedded within ORION's multimodal defense-in-depth architecture—which couples neural temporal priors with deterministic chromatic object grounding and formal safety invariants ($UNKNOWN \ne WRONG$, $UNCERTAIN \ne VIOLATION$)—the system achieves a **100.0% violation detection rate** on real Wrong Object and Wrong Order anomalies with **0.0% false violation alarms** across valid test protocols. Operating entirely offline without cloud dependencies, the full end-to-end pipeline achieves 21.2 FPS (49.6 ms latency) on Apple Silicon MPS hardware acceleration and ~11.1 FPS on CPU, with a standalone protocol decision throughput of 114,818 events/second. This work demonstrates that hybrid neuro-symbolic architectures provide a resilient, explainable, and flight-viable paradigm for autonomous astronaut assistance in safety-critical space missions.

**Keywords:** Human Activity Recognition, Procedural Protocol Validation, Spatio-Temporal Graph Convolutional Networks (ST-GCN), Neuro-Symbolic AI, Hand-Object Interaction, Edge AI, Bharatiya Antariksh Station (BAS), Aerospace Safety.

---

## 1. Introduction

Spaceflight microgravity experiments conducted inside orbital research facilities—such as the International Space Station (ISS), the Tiangong Space Station, and India's planned **Bharatiya Antariksh Station (BAS)**—are vital for advancing microgravity material sciences, protein crystallization, space medicine, and fluid dynamics. Astronauts onboard these platforms are required to execute complex, multi-step scientific protocols inside dedicated payload gloveboxes. However, crew members operate under severe cognitive load, physical confinement, microgravity-induced vestibular shifts, and intense time allocation pressures. Deviations from experimental procedures—such as manipulating an incorrect sample container, skipping critical incubation steps, or altering procedural sequence—can compromise irreproducible scientific payloads and waste thousands of mission operating hours.

To mitigate procedural errors, early mission designs relied on continuous ground-control telemetry and real-time audio-video downlinks. However, deep-space operations and low-Earth-orbit communication passes are constrained by ground-station line-of-sight gaps, restricted bandwidth, and transmission latency. Consequently, autonomous, onboard, edge-native computer vision systems capable of continuous observation, procedural state tracking, and immediate cognitive guidance are indispensable.

In this work, motivated by the Smart India Hackathon (SIH) Problem Statement **SIH26174** (*AI Human Activity Recognition for On-board BAS Experiments*), we investigate the design, empirical realities, and deployment constraints of **ORION**—an autonomous, edge-native AI copilot designed to observe spaceflight experiments via a fixed camera, understand human-object interactions, validate procedural sequences, provide real-time audio-visual guidance, and detect execution violations.

---

## 2. System Architecture

ORION decomposes procedural experiment understanding into a four-layer hierarchical architecture:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Perception Layer (CSI/USB Camera Ingestion @ 30 FPS)     │
│    - YOLO11n Object Detection (640x640, Bounding Boxes)     │
│    - YOLO11n-pose Pose Estimation (17 COCO Keypoints)       │
│    - ByteTrack Multi-Class Tracking (Kalman Filters)        │
├─────────────────────────────────────────────────────────────┤
│ 2. Interaction Layer (Zero-Latency Hand-Object Modeling)    │
│    - Kinematic Wrist/Elbow Geometric Hand Extraction        │
│    - Spatial Distance & IoU Contact State Machine           │
├─────────────────────────────────────────────────────────────┤
│ 3. Temporal AI Layer (ST-GCN Graph Convolutions)            │
│    - 32-Frame Sliding Window Buffer (Stride 8 Frames)       │
│    - 4-Channel Normalized Skeletal Tensor (x, y, dx, dy)    │
│    - Shannon Entropy Uncertainty Gating                     │
├─────────────────────────────────────────────────────────────┤
│ 4. Protocol Layer (Deterministic Invariant State Machine)   │
│    - Expected vs. Observed Action Matching                  │
│    - Lookahead Out-of-Sequence & Skipped Step Detection     │
│    - Offline Voice Synthesis, Local Recording & MJPEG Stream│
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Mathematical Formulation of ST-GCN

The human skeleton is modeled as an undirected graph $G = (V, E)$ with $V = 17$ joints. The spatial graph convolution with $K=3$ spatial partitions (root, centripetal, centrifugal) is defined as:

$$f_{out} = \sum_{k=1}^{K} \Lambda_k^{-\frac{1}{2}} A_k \Lambda_k^{-\frac{1}{2}} f_{in} W_k$$

where $A_k$ denotes the partitioned skeletal adjacency matrix, $\Lambda_k$ is the normalized degree matrix, and $W_k$ represents the learnable convolutional kernel weights.

Temporal modeling is achieved through 1D temporal convolutions with kernel size $K_t = 9$ across the 32-frame sliding buffer. Predictions are smoothed using an exponential moving average ($\alpha = 0.7$) and gated against Shannon entropy:

$$H(P) = -\sum_{c=1}^{C} P_c \ln(P_c)$$

If $H(P) > 1.40$ or $P_{\max} < 0.65$, the prediction is flagged as `STEP_UNCERTAIN` and suppressed, preventing false positive state advances.

---

## 4. Empirical Evaluation & Results

### 4.1 Neural Generalization Collapse in Small-$N$ Domains
On the custom `BAS_REAL_DATA` dataset (20 video recordings across 4 subjects), the ST-GCN model was evaluated under a strict zero-leakage subject-independent split (Train: `SP01`, `SP02`, `SP03`; Validation: `SP04`):

- **Training Accuracy (Epoch 25):** **95.56%** (Train Loss: 0.1475)
- **Validation Accuracy (Best):** **24.78%** (Val Loss: 4.3135)
- **Macro F1 Score:** **0.0146**

This empirical collapse confirms that in small-$N$ aerospace domains, purely kinematic neural networks cannot be trusted in isolation.

### 4.2 Neuro-Symbolic Resilience
When the neural predictions are coupled with chromatic object tracking and the formal FSM decision engine:
- **Anomaly Detection Rate (Wrong Object, Wrong Order):** **100.0%** (3/3 anomalies detected)
- **False Alarm Rate on Valid Test Protocols:** **0.0%**
- **Sustained Decision Engine Throughput:** **114,818.4 events/second** (Mean Latency: $0.0086\text{ ms}$)

### 4.3 Runtime Latency & Hardware Throughput
- **Apple Silicon MPS (Live Camera):** **21.2 FPS** (Mean Latency: $49.60\text{ ms}$)
- **Intel/Apple CPU Baseline:** **11.14 FPS** (Mean Latency: $89.58\text{ ms}$)
- **ST-GCN Forward Pass Latency:** **0.55 ms** (CPU)
- **Resident Set Size Memory:** **476.6 MB**

---

## 5. Limitations & Future Work

1. **Dataset Volume:** Expansion from 20 to 200+ multi-operator spaceflight sequences.
2. **3D Human Mesh Recovery:** Implementing lightweight orientation-agnostic 3D mesh regression for microgravity inversion invariance.
3. **Hardware Acceleration on Flight Silicon:** Benchmarking on space-qualified radiation-hardened SoCs and NVIDIA Jetson Orin.

---

## 6. Conclusion

ORION demonstrates that real-time human activity recognition and sequential protocol validation for space station experiments is feasible on standalone edge hardware. By pairing deep spatial-temporal graph neural networks with deterministic formal state machines, ORION overcomes the fundamental small-sample generalization collapse of deep learning, ensuring safe, reliable, and air-gapped mission execution for human spaceflight.
