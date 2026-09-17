# Dataset Curation & Microgravity Annotation Protocol

## Objective
Establish standardized procedures for collecting, cleaning, and annotating microgravity human activity and object interaction data.

## Annotation Topologies
- **Object Detection**: 2D Bounding Boxes formatted in COCO and YOLO standards with tight pixel margins.
- **Human Pose**: 17-keypoint COCO format (or 133 WholeBody format) including occlusion visibility flags (`v=0` unlabelled, `v=1` labeled but occluded, `v=2` clearly visible).
- **Temporal Action Segmentation**: Frame-accurate start/stop timestamps with action label annotations.

## Quality Gates
- Images with motion blur exceeding threshold are quarantined to `datasets/quality/rejected`.
- Missing frame sequences greater than 3 consecutive frames require manual review.
- All annotation manifests must include SHA-256 integrity checksums.
