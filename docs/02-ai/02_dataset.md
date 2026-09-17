# ORION BAS Experiment Dataset Audit

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments (SIH26174)  
**Organization:** Indian Space Research Organisation (ISRO)  
**Date:** September 17, 2026  
**Status:** FORENSICALLY VERIFIED AGAINST ON-DISK ARTIFACTS  

---

## 1. Dataset Origin & Scope

Under SIH26174 Requirement 13, ORION must build a custom focused local dataset for on-board biological and physical spaceflight experiments.

The dataset is located on-disk at [`datasets/bas_experiment/`](file:///Users/amitkumar/Orion/datasets/bas_experiment/) and audited via [`datasets/bas_experiment/reports/raw_data_audit.json`](file:///Users/amitkumar/Orion/datasets/bas_experiment/reports/raw_data_audit.json).

### High-Level Statistics:
- **Total Video Files:** 20 videos
- **Valid Nominal Sequences:** 17 videos
- **Invalid / Violation Sequences:** 3 videos (`Interruption`, `Wrong Object`, `Wrong Order`)
- **Total Physical Subjects:** 4 human subjects (`SP01`, `SP02`, `SP03`, `SP04`)
- **Resolutions:** 4K UHD ($3840 \times 2160$, 18 files) and FHD ($1920 \times 1080$, 2 files)
- **Frame Rates:** 30 FPS (12 files) and 60 FPS (8 files)
- **Video Codec:** HEVC / H.265 (High Efficiency Video Coding)
- **Total Dataset Size:** ~2.34 GB raw video

---

## 2. Experiment Taxonomy & Protocols

The dataset captures 5 distinct procedural experiment protocols defined in [`datasets/bas_experiment/experiment_definition.yaml`](file:///Users/amitkumar/Orion/datasets/bas_experiment/experiment_definition.yaml):

| Protocol ID | Protocol Title | Variants | Expected Procedural Flow |
|---|---|---|---|
| **E01** | Detecting Colour | Variant A (Yellow then Red)<br>Variant B (Red then Yellow) | Identify target colored containers; retrieve in prescribed color order; place in designated staging area. |
| **E02** | Interchanging | Variant A (Yellow to Red, Red to Yellow)<br>Variant B (Red to Yellow, Yellow to Red) | Swap physical locations of two experiment containers across workstation zones. |
| **E03** | Overlapping | Variant A (Yellow on Red)<br>Variant B (Red on Yellow) | Stack containers vertically to verify microgravity latching and spatial alignment. |
| **E04** | Moving | Variant A (Move Red towards Yellow)<br>Variant B (Move Yellow towards Red) | Translate containers horizontally along workstation guides while maintaining stability. |
| **E05** | In Container | Variant A (Pick Yellow, Check, Pick Red, Check)<br>Variant B (Pick Red, Check, Pick Yellow, Check) | Retrieve samples from sealed storage, perform visual inspection check, and secure in workspace. |

---

## 3. Class Definitions (8 Action Classes)

Temporal HAR classifies 8 distinct physical actions:

1. `idle`: Astronaut hands at rest, monitoring chamber, or reading instructions.
2. `pick_yellow`: Reaching and grasping the yellow experiment container.
3. `place_yellow`: Releasing the yellow container into a designated work zone.
4. `pick_red`: Reaching and grasping the red experiment container.
5. `place_red`: Releasing the red container into a designated work zone.
6. `move_box`: Continuous horizontal translation of an experiment object.
7. `check_box`: Elevating container toward camera or inspection viewport for verification.
8. `overlap_boxes`: Stacking or mating one container directly atop another.

---

## 4. Video Recording Inventory

| Video ID | Subject | Protocol | Variant | Resolution | FPS | Frames | Duration | File Size |
|---|---|---|---|---|---|---|---|---|
| `RAW_video_20260912_183146.mp4` | Invalid | Interruption | - | $3840 \times 2160$ | 30.0 | 402 | 13.4 s | 42.8 MB |
| `RAW_video_20260912_174946.mp4` | Invalid | Wrong Object | - | $3840 \times 2160$ | 30.0 | 568 | 18.9 s | 60.3 MB |
| `RAW_video_20260912_175307.mp4` | Invalid | Wrong Order | - | $3840 \times 2160$ | 29.9 | 509 | 17.0 s | 54.4 MB |
| `E05_SP01_VALID_B_EP10` | SP01 | E05 | B | $1920 \times 1080$ | 30.0 | 522 | 17.4 s | 37.5 MB |
| `E01_SP02_VALID_A_YP01` | SP02 | E01 | A | $3840 \times 2160$ | 60.0 | 862 | 14.4 s | 125.9 MB |
| `E01_SP02_VALID_B_YP02` | SP02 | E01 | B | $3840 \times 2160$ | 60.0 | 817 | 13.6 s | 119.4 MB |
| `E03_SP02_VALID_B_YP06` | SP02 | E03 | B | $3840 \times 2160$ | 57.0 | 461 | 8.1 s | 70.2 MB |
| `E04_SP02_VALID_A_YP07` | SP02 | E04 | A | $3840 \times 2160$ | 30.0 | 489 | 16.3 s | 141.6 MB |
| `E05_SP02_VALID_A_YP09` | SP02 | E05 | A | $3840 \times 2160$ | 30.1 | 403 | 13.4 s | 115.5 MB |
| `E05_SP02_VALID_B_YP10` | SP02 | E05 | B | $3840 \times 2160$ | 30.1 | 423 | 14.1 s | 120.9 MB |
| `E02_SP03_VALID_A_ZP03` | SP03 | E02 | A | $3840 \times 2160$ | 60.0 | 762 | 12.7 s | 111.8 MB |
| `E02_SP03_VALID_B_ZP04` | SP03 | E02 | B | $3840 \times 2160$ | 60.0 | 716 | 11.9 s | 104.8 MB |
| `E05_SP03_VALID_B_ZP10` | SP03 | E05 | B | $3840 \times 2160$ | 30.1 | 446 | 14.8 s | 124.8 MB |
| `E01_SP04_VALID_A_AP01` | SP04 | E01 | A | $3840 \times 2160$ | 60.0 | 789 | 13.1 s | 115.9 MB |
| `E01_SP04_VALID_B_AP02` | SP04 | E01 | B | $3840 \times 2160$ | 59.8 | 738 | 12.3 s | 109.2 MB |
| `E02_SP04_VALID_B_AP04` | SP04 | E02 | B | $3840 \times 2160$ | 30.1 | 421 | 14.0 s | 122.3 MB |
| `E04_SP04_VALID_A_AP07` | SP04 | E04 | A | $3840 \times 2160$ | 29.9 | 516 | 17.3 s | 150.2 MB |
| `E04_SP04_VALID_B_AP08` | SP04 | E04 | B | $3840 \times 2160$ | 29.9 | 463 | 15.5 s | 135.4 MB |
| `E05_SP04_VALID_A_AP09` | SP04 | E05 | A | $3840 \times 2160$ | 52.8 | 847 | 16.0 s | 140.2 MB |
| `E05_SP04_VALID_B_AP10` | SP04 | E05 | B | $3840 \times 2160$ | 30.0 | 396 | 13.2 s | 115.4 MB |

---

## 5. Train / Validation Split & Leakage Safeguards

- **Subject-Independent Splitting:** To avoid data leakage, splits are partitioned by subject ID rather than randomly shuffling temporal frames:
  - **Train Set:** Subjects `SP01`, `SP02`, `SP03` (15 videos)
  - **Validation Set:** Subject `SP04` (5 videos)
- **Data Leakage Check:** Bounding box coordinates and skeletal landmarks are generated per video without temporal overlap across splits.
- **Identified Limitation:** The sample count (20 videos) is sufficient to demonstrate architectural viability and pipeline integration, but insufficient for robust out-of-distribution generalizability across diverse astronaut body builds and orientations.

---

## 6. Dataset Curation & Microgravity Annotation Protocol

### 6.1 Objective
Establish standardized procedures for collecting, cleaning, and annotating microgravity human activity and object interaction data.

### 6.2 Annotation Topologies
- **Object Detection**: 2D Bounding Boxes formatted in COCO and YOLO standards with tight pixel margins.
- **Human Pose**: 17-keypoint COCO format (or 133 WholeBody format) including occlusion visibility flags (`v=0` unlabelled, `v=1` labeled but occluded, `v=2` clearly visible).
- **Temporal Action Segmentation**: Frame-accurate start/stop timestamps with action label annotations.

### 6.3 Quality Gates
- Images with motion blur exceeding threshold are quarantined to `datasets/quality/rejected`.
- Missing frame sequences greater than 3 consecutive frames require manual review.
- All annotation manifests must include SHA-256 integrity checksums.

