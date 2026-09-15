# ADR 010: Cryptographic Protocol Integrity & Evidence-Linked Audit Logging

## Status
Accepted

## Context
Space agency scientific payloads (e.g. ISRO BAS experiments) require post-flight and ground-link auditability. Ground scientists and flight controllers must be able to verify whether an experiment step was validated correctly, inspect the exact visual/pose evidence that led to that validation, and prove that the experiment protocol was not modified or corrupted mid-flight.

## Decision
1. **Cryptographic Protocol Hashing:** Every experiment protocol is canonicalized into deterministic JSON and hashed using SHA-256. The hash is recorded in the experiment metadata, embedded in telemetry, and stamped on every protocol execution run.
2. **Evidence-Linked Audit Trail:** Every decision evaluated by the `ProtocolDecisionEngine` generates a structured `ProtocolEvidence` record containing:
   - Frame window timestamps and frame indexes.
   - Actor track ID.
   - Keypoint coordinates and confidence scores.
   - Bounding box coordinates.
   - Softmax probability distribution and Shannon entropy score.
3. **SQLite Persistence:** Decisions and evidence are persisted to a dedicated `protocol_decisions` table in the local SQLite database via asynchronous event subscription.

## Consequences
### Positive
- Complete forensic traceability for every AI-validated action.
- Tamper-evident protocol specification verified against ground definitions.
- Offline-first: Full audit trail persisted locally without external network dependencies.

### Negative / Trade-offs
- Additional disk storage overhead in SQLite for storing evidence JSON payloads.
