# ORION BAS AI Copilot — Phase 1.4 Architecture
**Project:** ORION — BAS AI Copilot (`orion-bas-ai`)  
**SIH Problem Statement:** SIH26174 (*AI Human Activity Recognition for On-board BAS Experiments*)  
**Phase:** 1.4 — Protocol-Aware BAS Experiment Intelligence  
**Date:** September 2026  

---

## 1. System Overview

Phase 1.4 connects the computer vision perception layer (Phase 1.1–1.3) to the high-level operational intelligence layer. It translates raw spatio-temporal activity recognitions into structured scientific procedure tracking, anomaly detection, audit trail persistence, and real-time guidance for payload crew members.

```
+-----------------------------------------------------------------------------------+
|                            CAMERA & PERCEPTION (Phase 1.1-1.3)                    |
|  Camera Device -> CaptureWorker -> RingBuffer -> YOLOX Detector -> ByteTrack     |
|                   -> Hungarian Pose Association -> 32-frame Buffer -> ST-GCN HAR  |
+-----------------------------------------------------------------------------------+
                                         |
                                         | ActivityRecognized Event
                                         v
+-----------------------------------------------------------------------------------+
|                        ORION PROTOCOL INTELLIGENCE (Phase 1.4)                     |
|                                                                                   |
|  +---------------------------+       +-----------------------------------------+  |
|  | ActivityToActionMapper    | ----> | ProtocolDecisionEngine                  |  |
|  | - Class-to-Action mapping |       | - Confidence calibration (c >= 0.70)    |  |
|  | - Fallback & unmapped     |       | - Shannon Entropy filter (H <= 1.40)    |  |
|  +---------------------------+       | - Temporal debounce (K >= 2 windows)    |  |
|                                      | - Out-of-sequence & skip detection      |  |
|                                      +-----------------------------------------+  |
|                                                           |                       |
|                                                           v                       |
|  +---------------------------+       +-----------------------------------------+  |
|  | NextStepGuidanceEngine    | <---- | ProtocolStateMachine                    |  |
|  | - Step recommendations    |       | - 11 deterministic lifecycle states     |  |
|  | - Expected durations      |       | - Step index & sequence enforcement     |  |
|  | - Safety hazard warnings  |       | - Actor track consistency               |  |
|  +---------------------------+       +-----------------------------------------+  |
+-----------------------------------------------------------------------------------+
       |                                                    |
       v                                                    v
+-----------------------------+               +-------------------------------------+
| SQLite Persistence Layer    |               | WebSocket & REST Layer              |
| - experiments, runs, steps  |               | - /api/v1/experiments endpoints     |
| - protocol_decisions table  |               | - /ws/telemetry live streaming      |
| - Audit logs with SHA-256   |               | - React Cockpit HUD Real-time UI    |
+-----------------------------+               +-------------------------------------+
```

---

## 2. Core Architectural Components

### 2.1 Declarative Protocol Specification (`experiments/schemas.py`)
Protocols are defined entirely declaratively in YAML or JSON, eliminating hardcoded business logic in Python.
Each protocol defines:
- Metadata: `id`, `name`, `version`, `category`, `description`.
- Cryptographic hash: SHA-256 over normalized JSON representation.
- Preconditions, environment constraints, safety hazards.
- Ordered steps with `step_order`, `expected_actions`, `min_duration_s`, `max_duration_s`, `optional`, `allowed_transitions`, and `retry_policy`.

### 2.2 Semantic Translation Layer (`ActivityToActionMapper`)
Translates machine-learned activity predictions (`reach_tool`, `manipulate_sample`) into high-level protocol action requirements. Unmapped or unknown classes are gracefully mapped to `UNKNOWN` without triggering false anomalies.

### 2.3 Protocol Decision Engine (`ProtocolDecisionEngine`)
Evaluates incoming `ActivityRecognized` events against the active protocol step:
- **Confidence Calibration:** Requires $c \ge \text{threshold}$ (default: 0.70).
- **Entropy Check:** Requires Shannon entropy $H \le 1.40$ to reject ambiguous multi-class distributions.
- **Debounce Filter:** Requires $K \ge 2$ consecutive evaluation windows matching the expected action before confirming a step transition.
- **Safety Invariant Enforcers:**
  - `UNKNOWN != WRONG`: Maps to `WAITING_FOR_EVIDENCE`.
  - `UNCERTAIN != VIOLATION`: Maps to `STEP_UNCERTAIN`.
  - Step Skip Logic: Flags a step as `SKIPPED` only when a strictly subsequent step is observed with high confidence.

### 2.4 Finite State Machine (`ProtocolStateMachine`)
Manages execution lifecycle across 11 deterministic states:
`IDLE`, `LOADED`, `PRECHECK`, `RUNNING`, `STEP_IN_PROGRESS`, `STEP_COMPLETED`, `PAUSED`, `BLOCKED`, `COMPLETED`, `ABORTED`, `DEGRADED`.
Transitions between steps occur only when the Decision Engine yields `VALID_TRANSITION`.

### 2.5 Next-Step Guidance Engine (`NextStepEngine`)
Computes real-time crew guidance:
- Next expected physical activity.
- Step target duration and elapsed time countdown.
- Safety notes and procedural checklist items.

### 2.6 Persistence & Evidence Audit Trail (`ProtocolDecisionModel`)
Persists all protocol decisions in SQLite with:
- Timestamp, experiment ID, run ID, step ID.
- Observed action, expected action, decision status.
- Primary actor track ID.
- Evidence references: frame range, bounding box coordinates, keypoint confidence vector, Shannon entropy, raw probability distribution.

### 2.7 Frontend Cockpit HUD Integration
Streams experiment execution state via WebSocket:
- Protocol header with cryptographic hash and version.
- Step progress bar and active step highlights.
- Decision banner with color-coded safety indicators.
- Next-step recommendation box with action prompt and hazard warnings.
- Operator override controls (Start, Pause, Resume, Abort, Skip Step).
