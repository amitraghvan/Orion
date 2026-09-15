# ADR 009: Confidence-Calibrated Protocol Decision Engine & Safety Invariants

## Status
Accepted

## Context
Raw deep learning models (such as ST-GCN) output probabilistic activity classifications that fluctuate due to camera noise, partial occlusions, rapid microgravity motions, and boundary conditions between actions. If raw model predictions are evaluated directly against experiment rules without calibration, the copilot produces catastrophic false positive deviations (claiming the astronaut performed the wrong step) and false negative passes.

## Decision
We decouple raw model outputs from protocol state changes via a dedicated `ProtocolDecisionEngine`. The engine enforces three strict calibration layers and safety invariants:
1. **Confidence & Entropy Filtering:** A prediction is only admitted if $c \ge 0.70$ and its Shannon entropy $H(p) \le 1.40$. Highly ambiguous distributions yield `STEP_UNCERTAIN`, never a violation.
2. **Temporal Debounce Buffer ($K \ge 2$):** A step advance or state change requires $K \ge 2$ consecutive temporal observation windows (approximately 2 seconds of consistent motion) matching the expected action.
3. **Safety Invariants:**
   - `UNKNOWN != WRONG`: Unclassified actions yield `WAITING_FOR_EVIDENCE`, never protocol failures.
   - `NOT DETECTED != SKIPPED`: A step is only marked `SKIPPED` retroactively when a strictly subsequent step is observed with high confidence.

## Consequences
### Positive
- Drastically reduces false alarms in microgravity operational environments.
- Protects mission continuity by treating sensor uncertainty as uncertainty rather than crew error.
- Ensures robust, debounced state transitions.

### Negative / Trade-offs
- Adds approximately 1–2 windows (~1–2 s) of latency before confirming step completion. This latency is well within human experiment operation timescales.
