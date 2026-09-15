# ADR 015: Relational Normalization for Microgravity-Invariant Interaction Geometry

## Status
Accepted

## Context
In low Earth orbit (BAS microgravity modules), astronauts float without a fixed ground floor or gravity vector. Camera perspectives may drift, zoom, or be cropped, and subjects operate in variable roll/pitch/yaw orientations. Absolute pixel coordinates or ground-plane assumptions fail in this regime.

## Decision
1. **Relational Distance Metrics:** Measure hand-object distances relative to the subject's bounding diagonal ($d_{norm} = d_{px} / D_{ref}$), normalizing against body scale rather than static camera pixels.
2. **Asymmetric Overlap Ratio:** Use directed overlap $\frac{\text{Area}(\text{Hand} \cap \text{Object})}{\text{Area}(\text{Hand})}$ rather than symmetric IoU, ensuring small objects (e.g. 15ml centrifuge tube) held inside a larger hand region register high overlap.
3. **Orientation-Agnostic Vectors:** Use directional center offset vectors and relative approach velocities ($v_{approach} = \Delta d_{norm} / \Delta t$) rather than camera-axis velocities.

## Consequences
### Positive
- Fully invariant to crew distance from the camera, camera mounting rotation, and floating orientations.
- Correctly identifies grasps regardless of whether the astronaut is upright, inverted, or sideways relative to the payload rack.
- Highly resilient to scale variations across payload bays.

### Negative / Trade-offs
- If the primary actor's bounding box is severely truncated by frame boundaries, reference diagonal normalization requires clamping fallbacks.
