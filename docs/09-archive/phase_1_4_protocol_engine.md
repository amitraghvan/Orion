# ORION BAS AI Copilot — Phase 1.4 Protocol Engine Specification
**Project:** ORION — BAS AI Copilot (`orion-bas-ai`)  
**SIH Problem Statement:** SIH26174 (*AI Human Activity Recognition for On-board BAS Experiments*)  
**Phase:** 1.4 — Protocol-Aware BAS Experiment Intelligence  
**Date:** September 2026  

---

## 1. Protocol State Machine

### 1.1 State Taxonomy
The `ProtocolStateMachine` manages the lifecycle of an on-board experiment across 11 discrete, mutually exclusive states:

1. `IDLE`: Engine initialized, no experiment loaded.
2. `LOADED`: Experiment protocol loaded and verified with SHA-256 hash.
3. `PRECHECK`: Verifying workstation readiness, camera feed, and required tools.
4. `RUNNING`: Experiment execution active; waiting for step actions.
5. `STEP_IN_PROGRESS`: Crew member actively performing current step actions.
6. `STEP_COMPLETED`: Current step successfully validated; ready for next step.
7. `PAUSED`: Execution temporarily halted by operator; timers frozen.
8. `BLOCKED`: Deviation or safety hazard detected; awaits operator intervention or retry.
9. `COMPLETED`: All protocol steps completed successfully in valid sequence.
10. `ABORTED`: Experiment permanently stopped before completion by operator or critical hazard.
11. `DEGRADED`: Perception or engine failure detected; fail-safe mode active.

### 1.2 Transition Matrix

| Current State | Event / Trigger | Target State | Notes |
|---|---|---|---|
| `IDLE` | `load_protocol(protocol)` | `LOADED` | Computes & verifies SHA-256 hash |
| `LOADED` | `start_precheck()` | `PRECHECK` | Verifies camera, detector, models |
| `PRECHECK` | `start_experiment(run_id)` | `RUNNING` | Initializes Step 1 |
| `RUNNING` | `observation(debounce >= K)` | `STEP_IN_PROGRESS` | First confirmed action observed |
| `STEP_IN_PROGRESS` | `decision == VALID` | `STEP_COMPLETED` | Step criteria fulfilled |
| `STEP_COMPLETED` | `advance_step()` | `STEP_IN_PROGRESS` / `COMPLETED` | Advances to step $N+1$ or finishes |
| `RUNNING` / `STEP_IN_PROGRESS` | `pause()` | `PAUSED` | User or safety pause |
| `PAUSED` | `resume()` | `RUNNING` | Resumes timers & validation |
| Any active | `decision == OUT_OF_SEQUENCE` | `BLOCKED` | Non-fatal protocol deviation |
| `BLOCKED` | `operator_resolve(resolution)` | `RUNNING` / `STEP_IN_PROGRESS` | Explicit crew confirmation |
| Any active | `abort(reason)` | `ABORTED` | Permanent halt |
| Any | `internal_error` | `DEGRADED` | Fault isolation without crashing |

---

## 2. Decision Engine Evaluation Pipeline

### 2.1 Inputs to Decision Engine
For each `ActivityRecognized` event:
- `activity`: String label (`prepare_workstation`, `reach_tool`, `grasp_tool`, `manipulate_sample`, `inspect_chamber`, `idle`).
- `confidence`: Float in $[0, 1]$.
- `probabilities`: Dict mapping class labels to softmax probabilities.
- `track_id`: Integer actor identifier.
- `window_start_ts` / `window_end_ts`: Timestamps for the 32-frame window.

### 2.2 Evaluation Steps
1. **Model Uncertainty / Entropy Calculation:**
   $$H(p) = - \sum_{i=1}^M p_i \ln(p_i)$$
   If $H(p) > H_{\text{max}}$ (default: 1.40) or $\text{confidence} < c_{\text{min}}$ (default: 0.70):
   Yield `DecisionStatus.STEP_UNCERTAIN`. State does not advance; safety invariant preserved.

2. **Action Semantic Mapping:**
   Translate `activity` via `ActivityToActionMapper.map(activity)`. If unmapped, yield `DecisionStatus.WAITING_FOR_EVIDENCE`.

3. **Active Step Conformance:**
   Compare mapped action against `step.expected_actions`:
   - If match:
     - Increment debounce counter $k \leftarrow k + 1$.
     - If $k \ge K_{\text{debounce}}$ (default: 2):
       Yield `DecisionStatus.VALID`. If step duration constraints satisfied, transition to `STEP_COMPLETED`.
     - Else:
       Yield `DecisionStatus.WAITING_FOR_EVIDENCE` (debouncing).
   - If no match:
     - Reset debounce counter $k \leftarrow 0$.
     - Check if mapped action matches a *future* step in sequence:
       - If future step $j > \text{current}$:
         Yield `DecisionStatus.SKIPPED` (retroactive skip detected).
       - If past step $j < \text{current}$:
         Yield `DecisionStatus.OUT_OF_SEQUENCE`.
       - If action is `idle`:
         Yield `DecisionStatus.WAITING_FOR_EVIDENCE`.
       - Otherwise:
         Yield `DecisionStatus.INVALID_ACTION`.

4. **Temporal Duration Monitoring:**
   - If $\text{elapsed} > \text{max\_duration\_s}$:
     Yield `DecisionStatus.TIMEOUT`.
   - If action matches but $\text{elapsed} < \text{min\_duration\_s}$:
     Yield `DecisionStatus.WAITING_FOR_EVIDENCE` (minimum duration requirement not yet met).
