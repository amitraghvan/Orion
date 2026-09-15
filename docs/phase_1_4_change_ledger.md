# ORION BAS AI Copilot — Phase 1.4 Change Ledger
**Project:** ORION — BAS AI Copilot (`orion-bas-ai`)  
**SIH Problem Statement:** SIH26174 (*AI Human Activity Recognition for On-board BAS Experiments*)  
**Phase:** 1.4 — Protocol-Aware BAS Experiment Intelligence  
**Date:** September 2026  
**Status:** In Progress / Implementation  

---

## 1. Scope and Purpose
Phase 1.4 implements the protocol intelligence and scientific guidance layer of ORION. Building directly upon the frozen Phase 1.3 Spatio-Temporal HAR pipeline, Phase 1.4 introduces declarative protocol specifications, a multi-state finite state machine (FSM), deterministic sequence validation, confidence-calibrated decision evaluation with safety invariants, next-step guidance, SQLite persistence of evidence-linked audit trails, WebSocket telemetry broadcast, and an interactive React Cockpit HUD.

---

## 2. Inventory of Changes

| Component | Target File | Action | Description |
|---|---|---|---|
| **Architecture / ADR** | `docs/architecture/adr_008_protocol_state_machine.md` | NEW | ADR on 11-state deterministic protocol lifecycle FSM |
| **Architecture / ADR** | `docs/architecture/adr_009_protocol_decision_engine.md` | NEW | ADR on confidence-calibrated decision engine & safety invariants |
| **Architecture / ADR** | `docs/architecture/adr_010_evidence_linked_validation.md` | NEW | ADR on cryptographic protocol hashing & evidence traceability |
| **Documentation** | `docs/phase_1_4_architecture.md` | NEW | End-to-end Phase 1.4 system architecture |
| **Documentation** | `docs/phase_1_4_protocol_engine.md` | NEW | Detailed specification of state machine & decision engine |
| **Documentation** | `docs/phase_1_4_validation.md` | NEW | Conformance, timeout, retry, and safety policies |
| **Documentation** | `docs/phase_1_4_replay_scenarios.md` | NEW | Specification of the 15 golden scenario test cases |
| **Protocol Schema** | `experiments/schemas.py` | MODIFY | Add `expected_actions`, `allowed_transitions`, `optional`, `step_order` (backwards-compatible) |
| **Protocol Loader** | `experiments/loader.py` | NEW | Schema loader, structural validator, and canonical SHA-256 protocol hasher |
| **Canonical Protocol** | `configs/protocols/bas_crystal_growth_v1.yaml` | NEW | 6-step protein crystal growth protocol aligned with ST-GCN actions |
| **Evidence & Mapping** | `backend/src/orion/protocol/evidence.py` | NEW | Immutable Pydantic evidence container linking detections, keypoints, and HAR entropy |
| **Evidence & Mapping** | `backend/src/orion/protocol/action_mapping.py` | NEW | Explicit, versioned mapping between model classes and protocol action requirements |
| **Decision Engine** | `backend/src/orion/protocol/decision_engine.py` | NEW | Evaluation engine enforcing temporal debounce ($K \ge 2$), entropy thresholds, safety invariants |
| **State Machine** | `backend/src/orion/protocol/state_machine.py` | NEW | 11-state protocol lifecycle FSM with actor tracking & state history |
| **Next-Step Engine** | `backend/src/orion/protocol/next_step_engine.py` | NEW | Deterministic next-step guidance with countdown timer & parameter guidance |
| **Event Taxonomy** | `backend/src/orion/events/schemas.py` | MODIFY | Add `ProtocolStateChanged`, `StepTransitioned`, `ProtocolDeviationDetected`, `NextStepRecommended` |
| **ORM & Storage** | `backend/src/orion/db/models/decision.py` | NEW | `ProtocolDecisionModel` SQLite ORM table for indexed decision audit trail |
| **ORM Export** | `backend/src/orion/db/models/__init__.py` | MODIFY | Register `ProtocolDecisionModel` |
| **Persistence Worker** | `backend/src/orion/db/persistence_subscriber.py` | MODIFY | Consume and persist protocol events to SQLite |
| **Protocol Service** | `backend/src/orion/protocol/service.py` | NEW | Core service subscribing to `ActivityRecognized` and orchestrating engine components |
| **REST API** | `backend/src/orion/api/routers/experiments.py` | NEW | `/api/v1/experiments` REST endpoints for protocol management, execution lifecycle, audit |
| **App Assembly** | `backend/src/orion/main.py` & `app.py` | MODIFY | Mount router and register ProtocolService lifecycle |
| **WebSocket** | `backend/src/orion/api/routers/telemetry_ws.py` | MODIFY | Stream protocol state, step progress, decision events, and next-step recommendations |
| **Frontend Types** | `frontend/src/types/telemetry.ts` | MODIFY | TypeScript types for protocol state, steps, decisions, and recommendations |
| **Frontend Cockpit** | `frontend/src/App.tsx` | MODIFY | Add Experiment Copilot card, execution controls, decision banner, and step guidance |
| **Replay Script** | `scripts/replay_protocol_scenario.py` | NEW | CLI tool to inject synthetic or recorded HAR streams through Protocol Engine |
| **Benchmark Script** | `scripts/benchmark_protocol_engine.py` | NEW | Performance stress tester measuring throughput and latency under 10,000 events |
| **Unit Tests** | `tests/unit/test_protocol_engine.py` | NEW | Unit test suite for state machine, decision engine, and mapping |
| **Golden Scenarios** | `tests/golden/test_protocol_scenarios.py` | NEW | End-to-end execution of all 15 golden scenario test cases |
| **Integration Tests** | `tests/integration/test_protocol_api.py` | NEW | Integration test suite for REST API and persistence |

---

## 3. Safety Invariants Enforced
1. **UNKNOWN != WRONG**: Model prediction of `UNKNOWN` or unmapped actions yields `WAITING_FOR_EVIDENCE`, never a protocol violation.
2. **UNCERTAIN != VIOLATION**: High predictive entropy ($H > 1.4$) or confidence below threshold yields `STEP_UNCERTAIN`, never experiment failure.
3. **NOT DETECTED != SKIPPED**: A step is only classified as `SKIPPED` retroactively when a subsequent required step in the protocol sequence is verified with high confidence.
4. **TEMPORAL DEBOUNCE**: Step transition requires $K \ge 2$ consecutive observation windows matching the expected action.
5. **ACTOR INTEGRITY**: Multi-crew tracking ambiguities trigger `OPERATOR_REVIEW_REQUIRED`, never silent state advance.
6. **FAULT ISOLATION**: Internal protocol engine errors drop system status to `DEGRADED` without terminating camera capture or HAR inference.
