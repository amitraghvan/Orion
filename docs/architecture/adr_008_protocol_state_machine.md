# ADR 008: 11-State Deterministic Protocol Lifecycle Finite State Machine

## Status
Accepted

## Context
On-board BAS (Biological & Physical Sciences) experiment procedures aboard microgravity platforms require rigorous procedural compliance. The AI Copilot must track the global lifecycle of an experiment from initialization through step execution, pauses, deviations, and completion. A monolithic or ad-hoc boolean status system leads to race conditions, untracked partial states, and improper handling of operator pauses or emergency deviations.

## Decision
We implement an explicit 11-state deterministic Finite State Machine (`ProtocolStateMachine`) with typed transitions:
1. `IDLE`
2. `LOADED`
3. `PRECHECK`
4. `RUNNING`
5. `STEP_IN_PROGRESS`
6. `STEP_COMPLETED`
7. `PAUSED`
8. `BLOCKED`
9. `COMPLETED`
10. `ABORTED`
11. `DEGRADED`

Transitions are validated against a strict state transition table. Invalid transitions raise a typed `InvalidStateTransitionError` and do not mutate internal state.

## Consequences
### Positive
- Fully deterministic lifecycle guarantees that experiments cannot accidentally skip verification or jump into execution without pre-checks.
- Clean separation between overall experiment status and granular step progress.
- Safe pausing and operator resolution mechanisms for microgravity operational safety.

### Negative / Trade-offs
- Requires explicit transition events for all state changes.
- Slightly higher boilerplate compared to simple status strings.
