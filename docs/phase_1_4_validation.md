# ORION BAS AI Copilot — Phase 1.4 Validation Specification
**Project:** ORION — BAS AI Copilot (`orion-bas-ai`)  
**SIH Problem Statement:** SIH26174 (*AI Human Activity Recognition for On-board BAS Experiments*)  
**Phase:** 1.4 — Protocol-Aware BAS Experiment Intelligence  
**Date:** September 2026  

---

## 1. Safety Policies & Invariants

In microgravity space payload operations, false safety alarms cause mission disruption, while undetected procedural errors ruin irreplaceable biological samples. The validation layer enforces strict scientific policies:

### 1.1 Invariant 1: UNKNOWN != WRONG
- If an observed activity is unclassified (`UNKNOWN`), unmapped, or outside the trained model vocabulary, the engine emits `DecisionStatus.WAITING_FOR_EVIDENCE`.
- Under no circumstances does an `UNKNOWN` observation increment violation counters or trigger protocol abortion.

### 1.2 Invariant 2: UNCERTAIN != VIOLATION
- A prediction with confidence below threshold ($c < 0.70$) or Shannon entropy above threshold ($H > 1.40$) indicates sensory ambiguity (e.g., occlusion, motion blur, partial field of view).
- The engine emits `DecisionStatus.STEP_UNCERTAIN`. It logs the event with keypoint evidence and prompts the crew to confirm their posture without flagging a deviation.

### 1.3 Invariant 3: Retroactive Skip Verification
- A protocol step is never marked as `SKIPPED` merely because no action was observed during its nominal window.
- A step is only flagged as `SKIPPED` when a subsequent required step in the protocol sequence is verified with high confidence ($c \ge 0.70, H \le 1.40$) and temporal debounce ($k \ge 2$).

### 1.4 Invariant 4: Temporal Debouncing
- Transient classification fluctuations (e.g. 1 frame of spurious misclassification) are rejected.
- A step transition requires at least $K = 2$ consecutive windows (approx. 2.1 seconds of consistent human motion) matching the expected action.

### 1.5 Invariant 5: Multi-Person Tracking Disambiguation
- When multiple astronauts are in view, the protocol state machine binds to the primary experiment operator (`actor_track_id`).
- If an activity is detected from an unassigned track ID within the workstation bounding box, the engine prompts for operator disambiguation rather than falsely attributing the action.

---

## 2. Deviation & Recovery Strategies

When a genuine deviation occurs:
1. **Out-of-Sequence Action:** State machine transitions to `BLOCKED`. A `ProtocolDeviationDetected` event is fired.
2. **Step Timeout:** If step exceeds `max_duration_s`, the engine issues a warning alert and enters `BLOCKED` if critical, or requests crew confirmation to extend.
3. **Operator Resolution:** The crew or ground control can issue:
   - `PROCEED`: Accept the deviation and advance to next step.
   - `RETRY`: Reset the step timer and re-attempt the current step.
   - `ABORT`: Terminate the experiment run safely.
