# ADR 013: Deterministic Geometric Association & Temporal Hysteresis State Machine

## Status
Accepted

## Context
Human-Object Interaction (HOI) models in the academic literature often utilize large vision-language or graph neural networks that require heavy GPU compute and exhibit unexplainable false positives from single-frame optical artifacts or lighting changes. Spaceflight verification requires deterministic, mathematically auditable association.

## Decision
1. **Geometric Bipartite Matching:** Pair candidate hands and objects using Hungarian bipartite matching on a cost function combining normalized Euclidean distance and asymmetric bounding-box overlap.
2. **Temporal Hysteresis State Machine:** Enforce multi-frame persistence across state transitions:
   - `NO_INTERACTION` ➔ `APPROACHING` ➔ `NEAR` ➔ `CONTACT` ➔ `GRASPING` ➔ `MANIPULATING` ➔ `RELEASING` ➔ `LOST`.
3. **Flicker Rejection:** Require a minimum of 3 consecutive contact frames before asserting `GRASPING`, and 3 consecutive motion frames before asserting `MANIPULATING`. Single-frame optical overlaps are classified as transient `CONTACT` and do not trigger protocol completion.

## Consequences
### Positive
- Fully interpretable and deterministic: Zero black-box association failures.
- Robust against microgravity floating perturbations and transient occlusions.
- Real-time performance with sub-millisecond execution overhead (<0.5ms).

### Negative / Trade-offs
- Introduces a 2–3 frame (~60–100ms at 30 FPS) decision latency before certifying stable grasps, which is well within human action durations.
