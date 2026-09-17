# BAS Experiment Dataset Guide
**Project:** ORION — BAS AI Copilot  
**SIH Problem Statement:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments  
**Source Directory:** `/Users/amitkumar/Downloads/BAS_REAL_DATA`  
**Processed Dataset:** `datasets/bas_experiment/`

---

## 1. Raw Dataset Catalog

The raw video corpus consists of 20 MP4 video recordings captured at 1080x1920 (Portrait orientation) at 30.0 FPS.

### Subject & Protocol Mapping

| Filename | Subject ID | Experiment ID | Variant | Description | Duration | Split |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `EP01.mp4` | SP01 | E01 | A | Detecting Colour (Yellow then Red) | 13.9s | Train |
| `EP02.mp4` | SP01 | E01 | B | Detecting Colour (Red then Yellow) | 13.8s | Train |
| `EP03.mp4` | SP01 | E02 | A | Interchanging Boxes (Left to Right) | 13.1s | Train |
| `EP04.mp4` | SP01 | E02 | B | Interchanging Boxes (Right to Left) | 15.1s | Train |
| `EP05.mp4` | SP01 | E03 | A | Overlapping Boxes (Yellow on Red) | 16.0s | Train |
| `YP01.mp4` | SP02 | E01 | A | Detecting Colour (Yellow then Red) | 15.0s | Train |
| `YP02.mp4` | SP02 | E01 | B | Detecting Colour (Red then Yellow) | 14.9s | Train |
| `YP03.mp4` | SP02 | E02 | A | Interchanging Boxes (Left to Right) | 14.8s | Train |
| `YP04.mp4` | SP02 | E02 | B | Interchanging Boxes (Right to Left) | 15.9s | Train |
| `YP05.mp4` | SP02 | E03 | A | Overlapping Boxes (Yellow on Red) | 16.9s | Train |
| `ZP01.mp4` | SP03 | E01 | A | Detecting Colour (Yellow then Red) | 14.0s | Validation |
| `ZP02.mp4` | SP03 | E01 | B | Detecting Colour (Red then Yellow) | 14.5s | Validation |
| `ZP03.mp4` | SP03 | E02 | A | Interchanging Boxes (Left to Right) | 14.1s | Validation |
| `ZP04.mp4` | SP03 | E02 | B | Interchanging Boxes (Right to Left) | 14.9s | Validation |
| `ZP05.mp4` | SP03 | E03 | A | Overlapping Boxes (Yellow on Red) | 15.3s | Validation |
| `AP01.mp4` | SP04 | E01 | A | Detecting Colour (Yellow then Red) | 13.1s | Test |
| `AP02.mp4` | SP04 | E01 | B | Detecting Colour (Red then Yellow) | 13.1s | Test |
| `video_20260912_174946.mp4` | INVALID | E01 | A | Protocol Violation: Wrong Object | 18.9s | Test |
| `video_20260912_175307.mp4` | INVALID | E01 | A | Protocol Violation: Wrong Order | 17.0s | Test |
| `video_20260912_183146.mp4` | INVALID | E01 | A | Protocol Violation: Interruption | 13.4s | Test |

---

## 2. Feature Extraction Pipeline

Each video is processed by `scripts/prepare_bas_dataset.py`:
1. **Pose Estimation:** Ultralytics YOLO11n-pose detects 17 COCO skeletal keypoints.
2. **Chromatic HOI Tracking:** HSV mask segmentation locates red and yellow boxes and computes bounding box coordinates.
3. **Hand-Object Proximity:** Keypoint 9 (left wrist) and Keypoint 10 (right wrist) distances to box centroids are tracked per frame.
4. **Sliding Window:** Sequence windows of `window_size = 32` frames with `step_size = 8` frames (75% overlap).
5. **Tensor Shape:** `(4, 32, 17)` where:
   - Channel 0: Normalized X keypoint coordinate $[0.0, 1.0]$
   - Channel 1: Normalized Y keypoint coordinate $[0.0, 1.0]$
   - Channel 2: Pose keypoint detection confidence score $[0.0, 1.0]$
   - Channel 3: Normalized hand-object proximity distance $[0.0, 1.0]$

---

## 3. Dataset Artifacts

All processed dataset artifacts are saved under `datasets/bas_experiment/`:
- `sequences/`: 1,374 binary NumPy files (`.npy`) containing individual feature tensors.
- `metadata/manifest.jsonl`: Complete sequence index linking video ID, timestamps, labels, and tensor paths.
- `metadata/classes.json`: 8-class label index with ID mappings.
- `metadata/splits.json`: Zero-leakage subject partition index.
- `metadata/dataset_version.json`: Dataset version hash and provenance metadata (`BAS-DATA-v1.0.0`).
- `reports/raw_data_audit.json`: Programmatic audit of all 20 source MP4 files.
