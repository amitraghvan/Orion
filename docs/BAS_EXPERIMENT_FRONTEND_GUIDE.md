# ORION BAS AI Copilot — Frontend Demonstration Guide
**SIH Problem Statement:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments  
**Target Audience:** SIH Evaluation Judges, Evaluators, and Station Mission Operators  
**Demonstration Time:** 3 to 5 Minutes  
**UI URL:** `http://localhost:3000`  
**Backend API:** `http://localhost:8000`

---

## 1. System Overview

The ORION Station Cockpit is an edge-native, air-gapped human activity recognition (HAR) and protocol adherence platform designed specifically for the microgravity Biological Asteroid Station (BAS) and orbital laboratory modules (Gaganyaan / ISS).

### Key Architectural Highlights:
- **Trained on Real BAS Data:** Uses the actual `BAS_REAL_DATA` videos (`BAS-HAR-v1.0` weights trained directly on subjects SP01/SP02).
- **100% Air-Gapped & Offline:** Operates entirely locally on CPU / Apple Silicon MPS without internet or external cloud APIs.
- **Multimodal Hybrid Architecture:** Combines ST-GCN graph neural networks with chromatic Hand-Object Interaction (HOI) tracking and a deterministic Finite State Machine (FSM).
- **Voice Guidance Copilot:** Real-time synthesized acoustic advisories for procedure steps and safety violations.
- **Lightweight Structured Logging:** Zero-bloat telemetry streaming with one-click downloadable JSON audit logs.

---

## 2. Step-by-Step Judge Demonstration Script (3–5 Minutes)

### Phase 1: Station Status & Model Provenance (30 Seconds)
1. Point out the **Top Status Bar**:
   - **OFFLINE / EDGE** badge: Verifies system runs air-gapped on the station.
   - **MODEL: BAS-HAR-v1.0**: Indicates active neural weights trained on the BAS corpus.
   - **DATA: BAS-DATA-v1.0.0**: Verified zero-leakage subject-split dataset.
   - Real-time telemetry: Live camera connection, 30 FPS throughput, and sub-15ms perception latency.

### Phase 2: Valid Experiment Execution & Next-Step Guidance (90 Seconds)
1. In the **Experiment Copilot** panel:
   - Select **Experiment:** `E01 — Detecting Colour`
   - Select **Variant:** `A (Yellow then Red)`
2. In the **Optical Sensor Feed** toolbar:
   - In the dropdown, select **`AP01.mp4 — E01 Var A (SP04)`** (Held-out test subject).
   - Click **`PLAY VIDEO`**.
3. In the **Experiment Copilot** panel, click **`START RUN`**:
   - **Optical Feed:** Show live MJPEG playback with synchronized real-time overlays:
     - Green bounding boxes around yellow and red target apparatus.
     - Cyan 17-keypoint skeleton tracking astronaut posture.
     - Amber hand bounding boxes tracking wrist state.
     - Dynamic HOI vectors connecting astronaut hands to the manipulated box.
   - **Next Step Suggestion:** Show the blue guidance card updating dynamically as the astronaut completes each step:
     - Step 1: *Pick Yellow Box* → Step 2: *Place Yellow Box* → Step 3: *Pick Red Box* → Step 4: *Place Red Box*.
   - **Protocol Step Timeline:** Badges transition smoothly from `PENDING` → `IN PROGRESS` → `COMPLETED`.
   - **Completion:** When finished, the guidance card turns emerald: *"EXPERIMENT COMPLETED SUCCESSFULLY — 0 sequence violations detected."*

### Phase 3: Protocol Violation Detection & Voice Advisory (90 Seconds)
1. Select the violation test clip:
   - In the replay dropdown, select **`⚠ WRONG_OBJECT: video_20260912_174946.mp4`**.
   - Click **`PLAY VIDEO`**.
2. Observe the automated violation detection:
   - **Protocol Violation Alert:** A high-visibility rose warning panel triggers immediately:
     - Expected: `PICK_YELLOW`
     - Observed: `PICK_RED`
     - Confidence: `94%`
     - Status: `WRONG_OBJECT`
   - **Voice Alert System:** System audibly announces through speech synthesis:
     *"Warning. Expected pick yellow operation."*
   - **Decision Evidence Panel:** Shows full audit rationale with bounding box and overlap metrics explaining *why* the FSM blocked the operation.
3. Show operator recovery:
   - Click **`RETRY STEP`** or **`ACKNOWLEDGE & PROCEED`** to demonstrate operator-in-the-loop control.

### Phase 4: Structured Lightweight Mission Audit Log (30 Seconds)
1. Click **`AUDIT LOG`** in the Top Status Bar.
2. In the modal:
   - Show the summary breakdown: Run ID, Experiment ID, Steps Completed, and Recorded Violations.
   - Preview the structured JSON payload containing timestamped decision records.
   - Click **`Download JSON Log`** to show immediate export of `bas_mission_log_<run_id>.json`.
3. Highlight that video frames are decoupled from telemetry, ensuring the audit database remains compact (kilobytes rather than gigabytes).

---

## 3. Keyboard & Quick Shortcuts

- **Refresh Stream:** Click `PLAY VIDEO` on any selected clip to reload the video stream.
- **Switch to Live Camera:** Click `LIVE CAMERA (DEV 0)` to instantly return to physical camera device input.
- **Toggle Layers:** Use the `VIDEO`, `BOXES`, `SKELETON`, `HANDS`, `OBJECTS`, `HOI VECTORS` buttons to isolate perception subsystems.
