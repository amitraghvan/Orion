# ADR 014: Progressive Multimodal Evidence Fusion (Levels 0–3) & Conflict Detection

## Status
Accepted

## Context
Standard HAR classifies actions purely from skeletal kinematics. However, an astronaut mimicking a pipette grasp without the actual pipette represents a safety and protocol violation. Conversely, occlusions should not cause catastrophic pipeline failure. We require progressive fusion that verifies physical context without overwriting the raw neural activity prediction.

## Decision
1. **Immutable Dual-Track Telemetry:** Keep raw ST-GCN `ActivityRecognized` predictions immutable. Concurrently emit `MultimodalActivityEvidence` linking predictions to physical evidence.
2. **Progressive 4-Level Fusion:**
   - **Level 0:** Pure ST-GCN skeletal passthrough (baseline).
   - **Level 1:** ST-GCN + Object existence cross-check.
   - **Level 2:** ST-GCN + Object + Hand observability verification.
   - **Level 3:** Full physical validation (Skeletal HAR + Hand + Object + Temporal Interaction State).
3. **Active Conflict Detection:** Explicitly flag `CONFLICTING_EVIDENCE` when ST-GCN asserts a tool manipulation activity while optical sensors show no tool in the workspace or opposite interaction states.

## Consequences
### Positive
- Prevents false-positive protocol advancement when physical items are missing.
- Complete transparency: Scientists can see both the raw ML prediction and the physical evidence audit.
- Preserves backward compatibility with all Phase 1.3/1.4 consumers.

### Negative / Trade-offs
- Downstream systems must handle four discrete epistemic states (`FULL_EVIDENCE`, `PARTIAL_EVIDENCE`, `CONFLICTING_EVIDENCE`, `INSUFFICIENT_EVIDENCE`).
