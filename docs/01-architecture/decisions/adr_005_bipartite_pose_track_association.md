# Architectural Decision Record (ADR) 005: Optimal Hungarian Bipartite Matching for Pose-to-Track Association

## Status
**ACCEPTED** (2026-09-08)

## Context
Pose estimation and multi-object tracking are decoupled pipeline stages. Ultralytics YOLO-Pose outputs detected human skeletons with index-based IDs (`1, 2, ...`) corresponding to arbitrary forward-pass order. Meanwhile, ByteTrack assigns continuous, temporally consistent `track_id` integers to detected persons across consecutive video frames. If pose outputs are not explicitly associated with tracked identities, `person_id` flips across frames whenever astronauts move or cross paths, which would corrupt temporal Human Activity Recognition (HAR) feature buffers.

## Decision
1. In `PerceptionPipelineCoordinator`, enforce post-pose association using optimal bipartite matching via the Kuhn-Munkres (Hungarian) algorithm (`scipy.optimize.linear_sum_assignment`).
2. Construct a cost matrix between detected pose bounding boxes and active tracked person entities (`class_id == 0`):
   $$C_{i,j} = 1.0 - \text{IoU}(\text{pose}_i.\text{bbox}, \text{track}_j.\text{box})$$
3. Assign each pose the matched track's `track_id` when $\text{IoU} \ge 0.20$.
4. Unmatched poses fall back gracefully to sequential unassociated identifiers with diagnostic logging.

## Consequences
- **Positive**: Skeletons maintain guaranteed temporal identity consistency linked to tracked persons across occlusions and spatial translations. Direct prerequisite for reliable ST-GCN / Temporal HAR in Phase 1.3.
- **Negative**: Adds negligible Hungarian solve computation ($O(N^3)$ where $N \le 4$ crew members $\approx 0.02$ ms).
