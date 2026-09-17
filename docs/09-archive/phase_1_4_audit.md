# ORION — BAS AI Copilot: Phase 1.4 Forensic Audit
## Protocol-Aware BAS Experiment Intelligence
**SIH Problem Statement:** SIH26174 (*AI Human Activity Recognition for On-board BAS Experiments*)  
**Phase:** 1.4  
**Audit Standard:** Strict Forensic Traceability (`CLAIM -> CODE -> RUNTIME -> TEST -> EVIDENCE`)  
**Date:** September 2026  

---

### 1. Executive Summary

Phase 1.3 successfully established the first real spatio-temporal action recognition engine using a 4-block PyTorch ST-GCN network, achieving 12.90 FPS, 0.85 ms active HAR latency, and 59/59 passing tests. However, the system currently only knows *what* activity is being performed. It has no awareness of:
1. Which scientific procedure is currently running,
2. Whether the observed activity is procedurally legal at this step in the experiment,
3. What procedural step the astronaut should execute next,
4. Whether an action was skipped or performed out of sequence.

Phase 1.4 bridges this critical gap between **Perception** and **Scientific Guidance** by implementing an air-gapped, deterministic Protocol Intelligence Engine.

---

### 2. Forensic Codebase Audit

#### 2.1 Reusable Phase 1.3 Components
- **CLAIM:** `ActivityRecognized` events provide sufficient metadata for protocol consumption.
  - **CODE:** [backend/src/orion/events/schemas.py](file:///Users/amitkumar/Orion/backend/src/orion/events/schemas.py#L55-L70) (`track_id`, `frame_index`, `window_start_frame`, `window_end_frame`, `activity_label`, `phase`, `confidence`, `uncertainty_status`, `model_version`, `evidence_metadata`).
  - **RUNTIME:** Emitted synchronously during coordinator execution on stride triggers ($S=8$).
  - **TEST:** [tests/integration/test_temporal_har_pipeline.py](file:///Users/amitkumar/Orion/tests/integration/test_temporal_har_pipeline.py) verifies publication to `InMemoryEventBus`.
  - **EVIDENCE:** 193 events dispatched in benchmark, with 95 activities evaluated.

- **CLAIM:** Multi-person track isolation is already maintained in the temporal buffer.
  - **CODE:** [ai/src/orion_ai/activity/buffer.py](file:///Users/amitkumar/Orion/ai/src/orion_ai/activity/buffer.py#L55-L65).
  - **RUNTIME:** Isolated deques keyed by `track_id` with 30-frame stale eviction.
  - **TEST:** [tests/unit/test_har_multi_person.py](file:///Users/amitkumar/Orion/tests/unit/test_har_multi_person.py) passes.
  - **EVIDENCE:** 2 separate astronaut tracks produce isolated action streams without cross-contamination.

#### 2.2 Existing Protocol Scaffolding
- **CLAIM:** Phase 0 created placeholder experiment specifications in `experiments/`.
  - **CODE:** [experiments/schemas.py](file:///Users/amitkumar/Orion/experiments/schemas.py) defines `ExperimentSpecification`, `ExperimentMetadata`, `ExperimentObject`, `ExperimentStep`.
  - **RUNTIME:** [experiments/experiment_template.yaml](file:///Users/amitkumar/Orion/experiments/experiment_template.yaml) validates against Pydantic schema in [tests/contract/test_experiment_schema.py](file:///Users/amitkumar/Orion/tests/contract/test_experiment_schema.py).
  - **GAP:** `ExperimentStep` lacks `allowed_transitions`, `optional` flags, `retry_policy`, and `completion_policy`. The expected activities in the template (`pipette_aspiration`, `inject_reagent`) are decoupled from the 6 trained neural network classes.

#### 2.3 Database & ORM Storage
- **CLAIM:** SQLAlchemy ORM models exist for `experiments`, `runs`, and `steps`.
  - **CODE:** [backend/src/orion/db/models/experiment.py](file:///Users/amitkumar/Orion/backend/src/orion/db/models/experiment.py), [run.py](file:///Users/amitkumar/Orion/backend/src/orion/db/models/run.py), [step.py](file:///Users/amitkumar/Orion/backend/src/orion/db/models/step.py), and [event.py](file:///Users/amitkumar/Orion/backend/src/orion/db/models/event.py).
  - **RUNTIME:** SQLite persistence subscriber writes all durable events into `events` table.
  - **GAP:** No dedicated table or indexed query structure for `protocol_decisions` or evidence linking.

#### 2.4 Missing State-Machine & Reasoning Logic
- **CLAIM:** No finite-state machine currently coordinates experiment lifecycle or step transitions.
  - **CODE:** Currently absent.
  - **IMPACT:** System cannot distinguish `RUNNING` from `PAUSED` or evaluate out-of-sequence actions.
  - **ACTION:** Implement `ExperimentStateMachine` with 11 explicit operational states (`IDLE`, `ARMED`, `RUNNING`, `PAUSED`, `WAITING_FOR_EVIDENCE`, `STEP_VALIDATED`, `STEP_UNCERTAIN`, `STEP_FAILED`, `COMPLETED`, `ABORTED`, `DEGRADED`).

---

### 3. Safety & Epistemic Audit Findings

| ID | Area | Current State | Risk | Required Phase 1.4 Architecture |
| :--- | :--- | :--- | :--- | :--- |
| **AUD-01** | Epistemic Mapping | `UNKNOWN` from HAR | Conflating unobserved keypoints with wrong action | `UNKNOWN` must yield `WAITING_FOR_EVIDENCE`, never violation |
| **AUD-02** | Uncertainty Handling | $H > 1.4$ entropy | Conflating low confidence with step failure | `UNCERTAIN` state preserves step context and waits for evidence |
| **AUD-03** | Skip Detection | No retroactive check | Prematurely flagging missed steps on noise | Skip flagged only when *subsequent* valid step is verified |
| **AUD-04** | Debounce | Single raw frame | Single-frame action flutter advancing mission state | Require $K \ge 2$ consecutive stable windows before advance |
| **AUD-05** | Multi-Person Binding | First track id | Wrong astronaut action attributed to procedure | Explicit actor tracking policy with ambiguity alerts |
| **AUD-06** | Protocol Tampering | Plain text YAML | Silent corruption of flight procedures | SHA-256 integrity hash verified on load |
