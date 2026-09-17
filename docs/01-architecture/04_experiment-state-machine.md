# ORION Experiment State Machine & Sequence Validator

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments (SIH26174)  
**Organization:** Indian Space Research Organisation (ISRO)  
**Date:** September 17, 2026  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. High-Level State Transition Diagram

The protocol execution engine operates as a formal Finite State Machine (FSM) implemented in [`backend/src/orion/protocol/state_machine.py`](file:///Users/amitkumar/Orion/backend/src/orion/protocol/state_machine.py) and [`app/experiments/sequence_manager.py`](file:///Users/amitkumar/Orion/app/experiments/sequence_manager.py).

```
                      ┌───────────────┐
                      │     IDLE      │
                      └───────┬───────┘
                              │ load_protocol()
                              ▼
                      ┌───────────────┐
                      │     ARMED     │
                      └───────┬───────┘
                              │ start_execution()
                              ▼
                      ┌───────────────┐
            ┌────────►│    RUNNING    │◄──────────────┐
            │         └───────┬───────┘               │
            │                 │ begin_step()          │
            │                 ▼                       │
            │         ┌───────────────┐               │
            │         │    STEP IN    │               │
            │         │   PROGRESS    │               │
            │         └───────┬───────┘               │
            │                 │                       │
            │  step_success() │                       │
            └─────────────────┤                       │
                              │ violation / out-of-seq│
                              ▼                       │
                      ┌───────────────┐               │
                      │   VIOLATION   │               │
                      │  DETECTED     ├───────────────┘
                      └───────┬───────┘  (Non-fatal warning / resume)
                              │
             fatal exception  │ all steps complete
             ┌────────────────┼────────────────┐
             ▼                                 ▼
     ┌───────────────┐                 ┌───────────────┐
     │    FAILED     │                 │   COMPLETED   │
     └───────────────┘                 └───────────────┘
```

---

## 2. Protocol FSM States & Formal Definitions

| State Name | Enum Literal | Description | Allowed Next States |
|---|---|---|---|
| **IDLE** | `IDLE` | Default initial state. No protocol specification loaded. | `ARMED` |
| **ARMED** | `ARMED` | Protocol YAML loaded and parsed; step sequence compiled; awaiting start command. | `RUNNING`, `IDLE` |
| **RUNNING** | `RUNNING` | Mission run active; between discrete steps; awaiting astronaut action. | `STEP_IN_PROGRESS`, `PAUSED`, `ABORTED`, `COMPLETED` |
| **STEP_IN_PROGRESS**| `STEP_IN_PROGRESS`| Active step currently being executed and observed. | `RUNNING`, `PAUSED`, `FAILED` |
| **PAUSED** | `PAUSED` | Experiment execution temporarily halted by operator; timers frozen. | `RUNNING`, `ABORTED` |
| **ABORTED** | `ABORTED` | Manually cancelled before completion; terminal state for active run. | `IDLE` |
| **FAILED** | `FAILED` | Critical procedural violation or unrecoverable error; terminal state. | `IDLE` |
| **COMPLETED** | `COMPLETED` | All protocol steps verified and finalized successfully; mission accomplished. | `IDLE` |

---

## 3. Canonical BAS Experiment Sequence (Example: BAS-E01-A)

For Experiment E01 (Detecting Colour, Variant A), the protocol specification defines 4 mandatory steps:

```
[Start Run]
    │
    ▼
[Step 1: E01_A_S01] Pick Yellow Box from Station
    │ (Expected Action: "pick_yellow", Min Conf: 0.65, Max Entropy: 1.40, Debounce: 2)
    ▼
[Step 2: E01_A_S02] Inspect & Place Yellow Box into Inspection Area
    │ (Expected Action: "place_yellow")
    ▼
[Step 3: E01_A_S03] Pick Red Box from Station
    │ (Expected Action: "pick_red")
    ▼
[Step 4: E01_A_S04] Inspect & Place Red Box into Target Location
    │ (Expected Action: "place_red")
    ▼
[Experiment Complete]
```

---

## 4. Sequence Validation Invariants & Rules

The `ProtocolDecisionEngine` evaluates every incoming perception observation using 7 strict sequential checks:

### 1. Idle Awaiting Filter
If the recognized activity is `idle`, the system returns `WAITING_FOR_EVIDENCE` without penalizing the astronaut.

### 2. Confidence & Entropy Gating
If prediction confidence is below the step threshold ($\text{conf} < 0.65$) or normalized Shannon entropy is high ($H > 1.40$), the decision is marked `STEP_UNCERTAIN`. The system logs the marginal reading but refuses to advance the step.

### 3. Temporal Debouncing
To prevent single-frame false positives, an observed action must match the current step for at least $N$ consecutive temporal strides ($\text{debounce\_threshold} = 2$). If the streak is below threshold, status is `WAITING_FOR_EVIDENCE`.

### 4. Step In-Sequence Verification (`VALID`)
If the debounced action matches one of the active step's `expected_actions`:
- FSM records step completion.
- FSM automatically advances to the next step index ($k \leftarrow k + 1$).
- Voice alert synthesized: *"Step N completed. Please perform Step N+1."*
- Timestamped structured record written to database and log.

### 5. Wrong Object Manipulation (`WRONG_OBJECT`)
If the active step requires manipulating the Yellow box, but the astronaut manipulates the Red box (or vice versa):
- Decision status: `WRONG_OBJECT`.
- High-priority voice alert triggered: *"Warning. Wrong object manipulated."*
- Structured violation event recorded. FSM remains on the current step awaiting correction.

### 6. Out-of-Sequence & Skipped Step Detection (`OUT_OF_SEQUENCE`)
If the observed action does not match the active step $k$, the engine performs a look-ahead scan across all future steps $j \in [k+1, M]$:
- If action matches future step $j$:
  - All intermediate steps $[k, j-1]$ are retroactively identified as **SKIPPED**.
  - Decision status: `OUT_OF_SEQUENCE`.
  - Immediate voice warning: *"Warning. Out of sequence activity detected. Step j observed while Step k was expected."*
  - Operator dashboard displays an alert highlighting the skipped steps.

### 7. Unrecognized Procedural Action (`INVALID_ACTION`)
If an activity is performed that does not belong to any step in the protocol:
- Status: `INVALID_ACTION`.
- System alerts the astronaut: *"Unexpected activity executed during step N."*
