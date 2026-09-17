# PUBLICATION FIGURE SPECIFICATIONS & DATA PLANS: ORION
**Document ID:** ORION-FIG-2026-008  
**Classification:** Scientific Visualization Specifications  
**Date:** September 2026  
**Repository Path:** `/Users/amitkumar/Orion`  
**SIH Problem Statement:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments  

---

## Overview

In accordance with strict scientific publication rules, no fabricated plots or synthetic data are presented. For every figure, this document defines:
1. **Semantic Purpose & Scientific Context**
2. **Exact Data Provenance in Repository**
3. **Formal Visual Layout & ASCII / Graph Specification**
4. **Rendering Code / Scripts (if available)**

---

### Figure 1: Overall ORION Edge System Architecture
- **Type:** Conceptual Block Diagram / Systems Engineering Schematic
- **Purpose:** Illustrates the complete edge-native architecture spanning optical capture, perception DAG, temporal HAR, multimodal fusion, procedural FSM, event bus, and cockpit presentation.
- **Data Provenance:** Traced directly from `backend/src/orion/api/app.py`, `ai/src/orion_ai/runtime/coordinator.py`, and `backend/src/orion/protocol/service.py`.
- **Visual Structure:** Hierarchical layered architecture with vertical dataflow (Sensor $\to$ Perception $\to$ Reasoning $\to$ Presentation) and lateral persistence decoupling.

---

### Figure 2: Asynchronous Decoupled Pipeline & Ring-Buffer Flow
- **Type:** Data Flow / Queue Concurrency Diagram
- **Purpose:** Explains how the background capture worker thread (`collections.deque(maxlen=2)`), bounded client WebSocket queues (`maxsize=16`), and persistence queue (`maxsize=1000`) eliminate thread blocking and frame jitter.
- **Data Provenance:** Architectural Decision Records [adr_002](file:///Users/amitkumar/Orion/docs/architecture/adr_002_capture_worker_thread.md), [adr_003](file:///Users/amitkumar/Orion/docs/architecture/adr_003_inference_serialization_offload.md), and [adr_004](file:///Users/amitkumar/Orion/docs/architecture/adr_004_event_taxonomy_storage_decoupling.md).
- **Key Highlight:** Demonstrates how raw video frames bypass disk storage to ensure sub-80ms pipeline turnaround.

---

### Figure 3: Perception DAG & Zero-Latency Hand Extraction
- **Type:** Computer Vision Pipeline Diagram
- **Purpose:** Details the parallel execution of YOLO11n object detection and YOLO11n-pose estimation, followed by ByteTrack Kalman association and zero-overhead hand bounding box derivation from COCO wrist keypoints 9 & 10.
- **Data Provenance:** `ai/src/orion_ai/hand/extractor.py` and `ai/src/orion_ai/tracking/byte_tracker.py`.
- **Key Formula:** $p = \text{clamp}(0.08 \times \text{diag}_{\text{person}}, 20.0, 80.0)$ px.

---

### Figure 4: 4-Channel ST-GCN Graph Convolution & Spatial Partitioning
- **Type:** Deep Learning Neural Architecture Diagram
- **Purpose:** Visualizes the 17-keypoint COCO skeletal graph, the 3 spatial partitioning strategies (root, inward, outward), and the injection of hand-box proximity as the 4th tensor channel into the 4-block residual ST-GCN backbone.
- **Data Provenance:** `ai/src/orion_ai/activity/stgcn/model.py` and `ai/src/orion_ai/activity/stgcn/graph.py`.
- **Tensor Shapes:** Input $(B, 4, 32, 17) \to (B, 32, 32, 17) \to (B, 64, 16, 17) \to (B, 128, 16, 17) \to (B, 128, 8, 17) \to \text{Pool} \to (B, 128) \to \text{FC} \to (B, 8)$.

---

### Figure 5: Hand-Object Interaction (HOI) Geometry & Hysteresis FSM
- **Type:** State Diagram & Geometric Vector Illustration
- **Purpose:** Depicts the spatial metrics computed between hand centers and box bounding boxes (Euclidean distance, IoU, velocity) and the 5-state hysteresis machine (`NO_INTERACTION` $\to$ `APPROACHING` $\to$ `IN_CONTACT`/`GRASPING` $\to$ `MANIPULATING` $\to$ `RELEASING`).
- **Data Provenance:** `ai/src/orion_ai/interaction/geometry.py` and `ai/src/orion_ai/interaction/state_machine.py`.

---

### Figure 6: Deterministic 11-State Protocol Lifecycle FSM
- **Type:** Formal Automata / State Transition Diagram
- **Purpose:** Shows all 11 discrete states (`IDLE`, `LOADED`, `PRECHECK`, `RUNNING`, `STEP_IN_PROGRESS`, `STEP_COMPLETED`, `PAUSED`, `BLOCKED`, `COMPLETED`, `ABORTED`, `DEGRADED`), valid transition arrows, and recovery loops.
- **Data Provenance:** `backend/src/orion/protocol/state_machine.py` (`VALID_TRANSITIONS` dictionary).

---

### Figure 7: Cognitive Cockpit GUI Architecture
- **Type:** User Interface Component & Human-Machine Interaction Diagram
- **Purpose:** Illustrates how the React cockpit displays real-time telemetry: the optical canvas with synchronized skeleton/object/vector overlays, the Step Timeline, Next Step Guidance, Explainable Evidence Panel, and client-side Voice Alert dispatch.
- **Data Provenance:** `frontend/src/components/OpticalFeed.tsx` and `frontend/src/components/cockpit/`.

---

### Figure 8: End-to-End Latency Profile Breakdown (CPU vs. MPS)
- **Type:** Grouped Bar Chart / Latency Stack
- **Purpose:** Shows the latency breakdown across camera pop (0.09 ms), detection (35.71 ms CPU vs 12.72 ms MPS), pose (40.05 ms CPU vs 14.10 ms MPS), ByteTrack (0.05 ms), ST-GCN (1.24 ms CPU vs 0.42 ms MPS), and orchestration (0.47 ms).
- **Data Provenance:** `docs/phase_1_3_audit.md` and `docs/phase_1_5_audit.md`.

---

### Figure 9: Empirical ST-GCN Training & Validation Loss/Accuracy Curves
- **Type:** Double Line Chart (Epochs 1–25 vs Loss and Accuracy)
- **Purpose:** Plots the actual training progression on `BAS_REAL_DATA`. Demonstrates rapid training convergence (96.41% at epoch 25) alongside severe validation divergence (peak 24.78% at epoch 8, then dropping to ~20%), illustrating the cross-subject generalization gap.
- **Data Provenance:** Exact epoch-by-epoch loss and accuracy values in `models/bas_experiment/metrics.json`.

---

### Figure 10: Empirical 8×8 Confusion Matrix on Held-Out Test Data
- **Type:** Heatmap / Confusion Matrix
- **Purpose:** Displays the raw 8×8 prediction distribution on the 671 held-out test sequences (`SP04` + Anomaly clips). Highlights the concentration of predictions in `check_box` and `pick_red`, demonstrating the cross-subject failure mode of pure GCN classifiers.
- **Data Provenance:** `models/bas_experiment/evaluation.json` and `models/bas_experiment/confusion_matrix.png`.

---

### Figure 11: Real-World Sequence Validation Trace: Nominal vs. Violation
- **Type:** Dual Timeline Comparison Diagram
- **Purpose:** Compares the temporal progression of a nominal execution (`E01_SP04_VALID_A_AP01`: Pick Yellow $\to$ Place Yellow $\to$ Pick Red $\to$ Place Red) against a protocol violation (`RAW_video_20260912_174946.mp4`: Red box picked instead of Yellow box), showing how the FSM raises `WRONG_OBJECT` at $t=3.2$s with 100% confidence.
- **Data Provenance:** `datasets/bas_experiment/reports/raw_data_audit.json` and `models/bas_experiment/evaluation.json`.
