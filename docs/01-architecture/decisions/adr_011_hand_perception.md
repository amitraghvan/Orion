# ADR 011: Pose-Based Hand Perception and Wrist Region Extraction

## Status
Accepted

## Context
In microgravity BAS payload environments, fine-grained activity recognition requires distinguishing between empty hand postures, tool grasping, and sample manipulation. Running a secondary deep learning network specifically for hand landmark extraction (e.g. MediaPipe Hands or similar 21-keypoint model) incurs unacceptable inference latency and compute contention on edge-constrained space hardware (e.g., Jetson Orin Nano).

## Decision
1. **Pose-Derived Hand Seeding:** Leverage the primary YOLO-Pose 17-keypoint skeleton to extract hand spatial regions from wrist joints (COCO keypoints 9 and 10).
2. **Adaptive Bounding Region:** Expand the wrist keypoint coordinates into an adaptive bounding region scaled relative to the subject's torso/body diagonal, avoiding fixed-pixel artifacts across varying focal lengths and working distances.
3. **Multi-Tier Confidence States:** Classify hand observation states into `OBSERVED` (>0.5 score), `PARTIAL` (0.2–0.5), `OCCLUDED` (<0.2), and `MISSING`, providing explicit epistemic uncertainty to downstream interaction estimators.

## Consequences
### Positive
- Zero additional neural network forward passes, eliminating ~15–25ms of compute latency.
- Deterministic, air-gapped execution with no external library dependencies beyond the existing pose estimator.
- Graceful degradation: If hand keypoints are occluded, downstream state machines switch to `PARTIAL_EVIDENCE` without pipeline crashes.

### Negative / Trade-offs
- Does not extract 21 individual finger joint articulations; association relies on wrist spatial proximity and overlap geometry.
