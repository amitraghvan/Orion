# ORION BAS AI Copilot — Phase 1.4 Golden Replay Scenarios
**Project:** ORION — BAS AI Copilot (`orion-bas-ai`)  
**SIH Problem Statement:** SIH26174 (*AI Human Activity Recognition for On-board BAS Experiments*)  
**Phase:** 1.4 — Protocol-Aware BAS Experiment Intelligence  
**Date:** September 2026  

---

## 1. Overview
The Protocol Engine is validated against 15 deterministic golden replay scenarios. Each scenario simulates a sequence of `ActivityRecognized` events (or synthetic perception streams) to verify exact state transitions, decision statuses, and safety invariants.

---

## 2. The 15 Golden Test Cases

| ID | Scenario Name | Injected Event Sequence | Expected Terminal State & Verification |
|---|---|---|---|
| **SC-01** | Nominal Linear Execution | Steps 1 through 6 in exact order with debounce $K=2$ | Reaches `COMPLETED`, 6/6 steps valid, 0 deviations |
| **SC-02** | Out-of-Order Step Attempt | Step 1 -> Step 4 (`manipulate_sample` before tool reach) | Enters `BLOCKED`, emits `OUT_OF_SEQUENCE` decision |
| **SC-03** | Skipped Step Detection | Step 1 -> Step 2 -> Step 4 (Step 3 `grasp_tool` omitted) | Identifies Step 3 as `SKIPPED`, alerts operator |
| **SC-04** | Transient Noise Suppression | Step 1 -> (1 spurious `idle` or `grasp_tool`) -> Step 1 | Debounce holds; step remains active without resetting incorrectly |
| **SC-05** | High-Entropy Uncertainty | High entropy event ($H = 1.82 > 1.40$) during Step 2 | Emits `STEP_UNCERTAIN`, state remains in progress, no violation |
| **SC-06** | Low-Confidence Rejection | Expected action event with confidence $c = 0.45 < 0.70$ | Emits `STEP_UNCERTAIN`, does not trigger step advance |
| **SC-07** | Step Timeout Exceeded | Step 2 duration exceeds `max_duration_s` (120s) | Emits `TIMEOUT`, transitions to `BLOCKED` |
| **SC-08** | Operator Pause and Resume | Pause triggered during Step 3 -> resume after 30s | State toggles `PAUSED` then back to `RUNNING`; timers preserve elapsed |
| **SC-09** | Operator Abort Lifecycle | Explicit operator abort command during Step 4 | State enters `ABORTED`, logs reason, ceases evaluation |
| **SC-10** | Multi-Actor Tracking | Track 1 active, Track 2 transiently reaches into frame | Validates Track 1 actions, ignores or flags Track 2 interference |
| **SC-11** | Retry Failed Step | Step blocked -> Operator issues `RETRY` command | Resets step debounce and timer, returns to `STEP_IN_PROGRESS` |
| **SC-12** | Unknown Class Observation | Model outputs unmapped or `unknown` activity string | Emits `WAITING_FOR_EVIDENCE`, 0 violations incremented |
| **SC-13** | Rapid Succession Debounce | 10 rapid events within 200ms of alternating classes | Debounce filter stabilizes; prevents erratic state flapping |
| **SC-14** | Protocol Hash Tamper Detection | Modifying YAML step parameter after hash calculation | Rejects protocol load or flags integrity mismatch |
| **SC-15** | Fault-Isolated Recovery | Internal simulated exception in decision callback | System enters `DEGRADED`, captures error, perception stays alive |
