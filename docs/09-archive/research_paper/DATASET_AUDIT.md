# DATASET FORENSIC AUDIT: BAS_REAL_DATA
**Document ID:** ORION-DATASET-2026-003  
**Classification:** Experimental Dataset Forensic Audit  
**Date:** September 2026  
**Dataset Version:** `BAS-DATA-v1.0.0`  
**Raw Source Path:** `/Users/amitkumar/Downloads/BAS_REAL_DATA` (Archived in `datasets/bas_experiment/`)  
**SIH Problem Statement:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments  

---

## 1. Executive Summary

The `BAS_REAL_DATA` corpus consists of 20 real video recordings capturing human subjects performing spaceflight experiment protocols designed for the Bharatiya Antariksh Station (BAS). The raw dataset was programmatically audited via OpenCV and ffprobe to extract exact frame counts, durations, spatial resolutions, and frame rates.

To ensure strict compliance with scientific integrity and prevent train/test data leakage, the corpus was partitioned into a **zero-leakage subject-level split**. Frame-level shuffling across splits was strictly forbidden.

---

## 2. Complete Inventory of the 20 Raw Video Recordings

| Index | Video ID | Subject ID | Experiment ID | Variant | Validity | Anomaly Description | Duration (s) | Recorded FPS | Resolution | Total Frames | Assigned Split |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| 1 | `E05_SP01_VALID_B_EP10` | `SP01` | `E05` | B | VALID | Nominal execution | 17.39 | 30.02 | 1920x1080 | 522 | **Train** |
| 2 | `E01_SP02_VALID_A_YP01` | `SP02` | `E01` | A | VALID | Nominal execution | 14.38 | 59.95 | 3840x2160 | 862 | **Train** |
| 3 | `E01_SP02_VALID_B_YP02` | `SP02` | `E01` | B | VALID | Nominal execution | 13.63 | 59.95 | 3840x2160 | 817 | **Train** |
| 4 | `E03_SP02_VALID_B_YP06` | `SP02` | `E03` | B | VALID | Nominal execution | 8.09 | 56.99 | 3840x2160 | 461 | **Train** |
| 5 | `E04_SP02_VALID_A_YP07` | `SP02` | `E04` | A | VALID | Nominal execution | 16.30 | 30.00 | 3840x2160 | 489 | **Train** |
| 6 | `E05_SP02_VALID_A_YP09` | `SP02` | `E05` | A | VALID | Nominal execution | 13.40 | 30.07 | 3840x2160 | 403 | **Train** |
| 7 | `E05_SP02_VALID_B_YP10` | `SP02` | `E05` | B | VALID | Nominal execution | 14.07 | 30.07 | 3840x2160 | 423 | **Train** |
| 8 | `E02_SP03_VALID_A_ZP03` | `SP03` | `E02` | A | VALID | Nominal execution | 12.71 | 59.95 | 3840x2160 | 762 | **Validation** |
| 9 | `E02_SP03_VALID_B_ZP04` | `SP03` | `E02` | B | VALID | Nominal execution | 11.94 | 59.95 | 3840x2160 | 716 | **Validation** |
| 10 | `E05_SP03_VALID_B_ZP10` | `SP03` | `E05` | B | VALID | Nominal execution | 14.84 | 30.06 | 3840x2160 | 446 | **Validation** |
| 11 | `E01_SP04_VALID_A_AP01` | `SP04` | `E01` | A | VALID | Nominal execution | 13.14 | 60.03 | 3840x2160 | 789 | **Test** |
| 12 | `E01_SP04_VALID_B_AP02` | `SP04` | `E01` | B | VALID | Nominal execution | 12.34 | 59.79 | 3840x2160 | 738 | **Test** |
| 13 | `E02_SP04_VALID_B_AP04` | `SP04` | `E02` | B | VALID | Nominal execution | 14.00 | 30.07 | 3840x2160 | 421 | **Test** |
| 14 | `E04_SP04_VALID_A_AP07` | `SP04` | `E04` | A | VALID | Nominal execution | 17.27 | 29.88 | 3840x2160 | 516 | **Test** |
| 15 | `E04_SP04_VALID_B_AP08` | `SP04` | `E04` | B | VALID | Nominal execution | 15.50 | 29.87 | 3840x2160 | 463 | **Test** |
| 16 | `E05_SP04_VALID_A_AP09` | `SP04` | `E05` | A | VALID | Nominal execution | 16.04 | 52.80 | 3840x2160 | 847 | **Test** |
| 17 | `E05_SP04_VALID_B_AP10` | `SP04` | `E05` | B | VALID | Nominal execution | 13.20 | 30.00 | 3840x2160 | 396 | **Test** |
| 18 | `RAW_video_20260912_174946.mp4` | `SUB_INV` | `E01` | A | **INVALID** | **Wrong Object** (Red picked instead of Yellow) | 18.93 | 30.00 | 3840x2160 | 568 | **Test** |
| 19 | `RAW_video_20260912_175307.mp4` | `SUB_INV` | `E01` | A | **INVALID** | **Wrong Order** (Red step executed prior to Yellow) | 17.01 | 29.93 | 3840x2160 | 509 | **Test** |
| 20 | `RAW_video_20260912_183146.mp4` | `SUB_INV` | `E01` | A | **INVALID** | **Interruption** (Operator pauses / walks away) | 13.38 | 30.05 | 3840x2160 | 402 | **Test** |

### Aggregate Dataset Metrics:
- **Total Number of Videos:** 20
- **Total Valid Videos:** 17
- **Total Invalid / Anomaly Videos:** 3
- **Total Subjects Recorded:** 4 designated subjects (`SP01`, `SP02`, `SP03`, `SP04`) plus 1 unassigned anomaly operator (`SUB_INVALID`)
- **Total Recorded Video Duration:** 287.62 seconds (~4.8 minutes)
- **Total Video Frames:** 11,550 frames
- **Spatial Resolutions:** 1 clip at Full HD (1920×1080 portrait), 19 clips at 4K UHD (3840×2160 portrait)
- **Capture Frame Rates:** Mixed ~30 FPS (12 clips) and ~60 FPS (8 clips)

---

## 3. Experiment Categories & Ground Truth Protocols

The dataset exercises 5 distinct spaceflight experiment categories, each containing two execution variants:

### E01 — Detecting Colour
- **Variant A:** Pick Yellow Box $\to$ Return Yellow Box $\to$ Pick Red Box $\to$ Return Red Box.
- **Variant B:** Pick Red Box $\to$ Return Red Box $\to$ Pick Yellow Box $\to$ Return Yellow Box.

### E02 — Interchanging Boxes
- **Variant A:** Pick both boxes $\to$ Place Yellow on Red's slot $\to$ Place Red on Yellow's slot.
- **Variant B:** Pick both boxes $\to$ Place Red on Yellow's slot $\to$ Place Yellow on Red's slot.

### E03 — Overlapping Boxes
- **Variant A:** Place two boxes (Red and Yellow) $\to$ Stack Yellow on top of Red.
- **Variant B:** Place two boxes (Red and Yellow) $\to$ Stack Red on top of Yellow.

### E04 — Moving Boxes
- **Variant A:** Yellow remains in respective place $\to$ Move Red box towards Yellow box.
- **Variant B:** Red remains in respective place $\to$ Move Yellow box towards Red box.

### E05 — In Container
- **Variant A:** Pick Yellow box from container $\to$ Inspect/Check $\to$ Pick Red from container $\to$ Inspect/Check.
- **Variant B:** Pick Red box from container $\to$ Inspect/Check $\to$ Pick Yellow from container $\to$ Inspect/Check.

---

## 4. Feature Extraction & Window Segmentation

Using `scripts/prepare_bas_dataset.py`, each video was processed into temporal feature sequence arrays of shape `(4, 32, 17)`:
1. **Pose Extraction:** 17 2D keypoints per frame extracted via YOLO11n-pose.
2. **Chromatic Target Localization:** Color segmentation in HSV space identifies Yellow Box ($\text{Hue} \in [15, 35]$) and Red Box ($\text{Hue} \in [0, 10] \cup [170, 180]$).
3. **Proximity Scoring:** For wrist keypoints $W = (x, y)$, normalized Euclidean proximity to the nearest bounding box is computed:
   $$p_{\text{prox}} = \max\left(0.0, 1.0 - \frac{\min_b \|W - c(b)\|_2}{0.25 \times \text{diag}_{\text{frame}}}\right)$$
4. **Channel Encoding:**
   - Channel 0: Normalized joint $X \in [0, 1]$
   - Channel 1: Normalized joint $Y \in [0, 1]$
   - Channel 2: Keypoint confidence score $s \in [0, 1]$
   - Channel 3: Hand-box interaction proximity $p_{\text{prox}} \in [0, 1]$
5. **Windowing:** Window length $T=32$ frames, Stride $S=8$ frames.

### Canonical Class Distribution (Total: 1,374 Sequences):
- Class 0: `idle`
- Class 1: `pick_yellow`
- Class 2: `place_yellow`
- Class 3: `pick_red`
- Class 4: `place_red`
- Class 5: `move_box`
- Class 6: `check_box`
- Class 7: `overlap_boxes`

---

## 5. Zero-Leakage Subject-Level Split

To prevent optimistic bias and test true generalization to unseen human operators, videos were partitioned strictly by subject identity (`datasets/bas_experiment/metadata/splits.json`):

| Split | Subject IDs Included | Video Count | Sequences Extracted | Percentage of Dataset |
| :--- | :--- | :---: | :---: | :---: |
| **Train Set** | `SP01` (EP), `SP02` (YP) | 7 clips | 473 | 34.4% |
| **Validation Set** | `SP03` (ZP) | 3 clips | 230 | 16.7% |
| **Test Set (Held-Out)** | `SP04` (AP) + `SUB_INV` | 10 clips (7 valid + 3 invalid) | 671 | 48.8% |
| **Total** | **4 subjects + 1 invalid** | **20 clips** | **1,374** | **100.0%** |

### Leakage Verification:
- **Frame-level overlap across splits:** **0.0% (Verified)**
- **Subject-level overlap across splits:** **0.0% (Verified)**

---

## 6. Dataset Quality & Methodological Critique

### Strengths:
1. **Real-World Observation:** Involves genuine physical manipulation of designated colored apparatus on real tables, rather than synthetic keypoint renders.
2. **Multi-Camera & Resolution Realism:** Features varied frame rates (30 vs 60 FPS) and mixed resolutions (1080p vs 4K), reflecting sensor diversity in flight racks.
3. **Dedicated Anomaly Suite:** Three real anomaly videos capturing physical violations (Wrong Object, Wrong Order, Interruption).

### Methodological Limitations:
1. **Extremely Small Sample Size ($N=4$):** Only 4 human subjects were recorded. In deep learning, $N=4$ subjects is severely insufficient for high-dimensional neural generalization across unseen morphological variations.
2. **Kinematic & Viewpoint Discrepancies:** Held-out subject `SP04` operated at a noticeably different table distance, camera pitch angle, and execution speed compared to `SP01` and `SP02`.
3. **Severe Class Imbalance:** Within the held-out test split, `idle` accounts for 215 sequences, while `overlap_boxes` has 0 test sequences.
4. **Controlled Ground Lab Setting:** All recordings were captured under 1-g laboratory conditions; true microgravity floating dynamics (e.g. foot restraints, floating objects) are not represented in the physical video pixels.
