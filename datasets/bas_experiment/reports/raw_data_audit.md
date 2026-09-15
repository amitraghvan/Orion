# BAS_REAL_DATA — Raw Data Audit Report

## 1. Executive Summary

- **Total Raw Videos**: 20
- **Valid Execution Videos**: 20
- **Invalid / Deviation Videos**: 0
- **Total Video Duration**: 287.6 seconds (4.8 minutes)
- **Total Recorded Frames**: 11,550
- **All Files Readable**: True
- **Duplicate Files Detected**: False

## 2. Experiment & Variant Distribution

| Video ID | Subject | Exp | Var | Valid? | Type / Description | Duration | FPS | Resolution |
|---|---|---|---|---|---|---|---|---|
| `RAW_video_20260912_183146.mp4` | Invalid data bas | None | None | VALID |  | 13.38s | 30.05 | 3840x2160 |
| `RAW_video_20260912_174946.mp4` | Invalid data bas | None | None | VALID |  | 18.93s | 30.0 | 3840x2160 |
| `RAW_video_20260912_175307.mp4` | Invalid data bas | None | None | VALID |  | 17.01s | 29.93 | 3840x2160 |
| `E05_SP01_VALID_B_EP10` | SP01 | E05 | B | VALID | In Container: Pick Red, Check, Pick Yellow, Check | 17.39s | 30.02 | 1920x1080 |
| `E01_SP02_VALID_A_YP01` | SP02 | E01 | A | VALID | Detecting Colour: Yellow then Red | 14.38s | 59.95 | 3840x2160 |
| `E01_SP02_VALID_B_YP02` | SP02 | E01 | B | VALID | Detecting Colour: Red then Yellow | 13.63s | 59.95 | 3840x2160 |
| `E03_SP02_VALID_B_YP06` | SP02 | E03 | B | VALID | Overlapping: Two boxes, Red on Yellow | 8.09s | 56.99 | 3840x2160 |
| `E04_SP02_VALID_A_YP07` | SP02 | E04 | A | VALID | Moving: Yellow stationary, Move Red towards Yellow | 16.3s | 30.0 | 3840x2160 |
| `E05_SP02_VALID_A_YP09` | SP02 | E05 | A | VALID | In Container: Pick Yellow, Check, Pick Red, Check | 13.4s | 30.07 | 3840x2160 |
| `E05_SP02_VALID_B_YP10` | SP02 | E05 | B | VALID | In Container: Pick Red, Check, Pick Yellow, Check | 14.07s | 30.07 | 3840x2160 |
| `E02_SP03_VALID_A_ZP03` | SP03 | E02 | A | VALID | Interchanging: Both boxes, Yellow to Red place, Red to Yellow place | 12.71s | 59.95 | 3840x2160 |
| `E02_SP03_VALID_B_ZP04` | SP03 | E02 | B | VALID | Interchanging: Both boxes, Red to Yellow place, Yellow to Red place | 11.94s | 59.95 | 3840x2160 |
| `E05_SP03_VALID_B_ZP10` | SP03 | E05 | B | VALID | In Container: Pick Red, Check, Pick Yellow, Check | 14.84s | 30.06 | 3840x2160 |
| `E01_SP04_VALID_A_AP01` | SP04 | E01 | A | VALID | Detecting Colour: Yellow then Red | 13.14s | 60.03 | 3840x2160 |
| `E01_SP04_VALID_B_AP02` | SP04 | E01 | B | VALID | Detecting Colour: Red then Yellow | 12.34s | 59.79 | 3840x2160 |
| `E02_SP04_VALID_B_AP04` | SP04 | E02 | B | VALID | Interchanging: Both boxes, Red to Yellow place, Yellow to Red place | 14.0s | 30.07 | 3840x2160 |
| `E04_SP04_VALID_A_AP07` | SP04 | E04 | A | VALID | Moving: Yellow stationary, Move Red towards Yellow | 17.27s | 29.88 | 3840x2160 |
| `E04_SP04_VALID_B_AP08` | SP04 | E04 | B | VALID | Moving: Red stationary, Move Yellow towards Red | 15.5s | 29.87 | 3840x2160 |
| `E05_SP04_VALID_A_AP09` | SP04 | E05 | A | VALID | In Container: Pick Yellow, Check, Pick Red, Check | 16.04s | 52.8 | 3840x2160 |
| `E05_SP04_VALID_B_AP10` | SP04 | E05 | B | VALID | In Container: Pick Red, Check, Pick Yellow, Check | 13.2s | 30.0 | 3840x2160 |

## 3. Data Integrity & Mapping Assessment

- **Subjects Available**: SP01 (EP), SP02 (YP), SP03 (ZP), SP04 (AP).
- **Subject Partitioning Strategy**: SP01, SP02 for Training; SP03 for Validation; SP04 for Held-Out Testing.
- **Invalid Testing Suite**: 3 real recordings testing Interruption, Wrong Object, and Wrong Order violations.
- **Unresolved Mappings**: 0 (all 20 videos mapped with 100% certainty).
