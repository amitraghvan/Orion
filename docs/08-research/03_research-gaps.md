# ORION Scientific Research Gaps Analysis

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments (SIH26174)  
**Organization:** Indian Space Research Organisation (ISRO)  
**Date:** September 17, 2026  
**Status:** FORENSIC SCIENTIFIC GAP ANALYSIS  

---

## 1. Summary of Primary Research Gaps

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Dataset Scale & Generalization (Validation Acc: 24.78%)   │
├─────────────────────────────────────────────────────────────┤
│ 2. Microgravity Orientation & 3D Human Mesh Recovery (HMR)  │
├─────────────────────────────────────────────────────────────┤
│ 3. Severe Self-Occlusion Inside Confined Glovebox Enclosures│
├─────────────────────────────────────────────────────────────┤
│ 4. Fine-Grained Tool & Specialized Object Perception        │
├─────────────────────────────────────────────────────────────┤
│ 5. Continuous Temporal Boundary Segmentation                │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Gap-by-Gap Breakdown

### Gap 1: Limited Dataset Scale & Generalization Gap
- **Problem:** Significant overfitting between training accuracy ($95.56\%$) and validation accuracy ($24.78\%$).
- **Why It Matters:** In real spaceflight operations, an AI copilot that fails to recognize an astronaut's movements due to minor differences in reach angle or cadence will emit false violation alerts, causing operator frustration and lack of trust.
- **Empirical Evidence:** Checked against [`models/bas_experiment/metrics.json`](file:///Users/amitkumar/Orion/models/bas_experiment/metrics.json): Train Acc reaches 95.56% at epoch 25, but Val Acc plateaus at 24.78%.
- **Current Limitation:** The dataset contains 20 raw video files (17 valid, 3 invalid) across 4 subjects.
- **Potential Solution:**
  1. Synthetic kinetic trajectory augmentation (random 3D skeletal rotation, temporal stretching, Gaussian joint perturbation).
  2. Multi-subject expansion to 200+ video recordings across varied body anthropometries.
- **Difficulty:** Moderate.
- **Expected Impact:** Expected to raise validation accuracy from $24.78\%$ to $>85.0\%$.

---

### Gap 2: Orientation-Agnostic 3D Human Mesh Recovery (HMR)
- **Problem:** SIH26174 lists 3D HMR as an optional capability. In zero-gravity, astronauts do not have a defined "up" or "down" vector; they operate inverted, sideways, and in neutral body posture (NBP).
- **Why It Matters:** 2D skeleton estimation suffers severe joint foreshortening and depth ambiguity when the camera views an astronaut from an oblique microgravity angle.
- **Empirical Evidence:** Current system uses 2D torso-centering and scale normalization. While effective for frontal/near-frontal views, out-of-plane rotations degrade 2D joint detection confidence.
- **Current Limitation:** Full 3D SMPL/SMPL-X mesh recovery models (e.g., CLIFF, HMR 2.0) require 150+ GFLOPs and 4+ GB of dedicated VRAM, exceeding lightweight edge targets.
- **Potential Solution:** Distill a lightweight 3D mesh regressor (e.g., FastHMR) predicting 3D joint rotations from 2D skeletons rather than raw pixels.
- **Difficulty:** High.
- **Expected Impact:** Complete orientation invariance regardless of astronaut microgravity floating posture.

---

### Gap 3: Optical Distortion & Glovebox Occlusion
- **Problem:** Glovebox acrylic viewports induce optical reflections, glare from internal LED strips, and severe forearm occlusion when hands reach deep into specimen chambers.
- **Why It Matters:** Wrist keypoints can be lost when hands penetrate beneath glovebox baffles, disrupting HOI distance calculations.
- **Empirical Evidence:** Audited in [`datasets/bas_experiment/reports/raw_data_audit.json`](file:///Users/amitkumar/Orion/datasets/bas_experiment/reports/raw_data_audit.json) on E05 "In Container" recordings where hands enter closed containers.
- **Current Limitation:** When keypoints drop below confidence 0.3, hand extraction defaults to previous Kalman position.
- **Potential Solution:** Multi-camera temporal tracking combining overhead and lateral glovebox angles via Hungarian multi-view fusion.
- **Difficulty:** Moderate.
- **Expected Impact:** 99.5% tracking continuity through deep chamber reaches.

---

### Gap 4: Domain-Specific Object Detection Fine-Tuning
- **Problem:** Pretrained YOLO11n weights are trained on general COCO classes (`bottle`, `cup`, `chair`, `scissors`), rather than specific ISRO spaceflight apparatus.
- **Why It Matters:** Custom containers (e.g., BAS biological reaction vials, latch mechanisms) must be detected with high precision under varying flight lighting.
- **Empirical Evidence:** In `app/intelligence/intelligence_engine.py`, generic detection bounding boxes are mapped to `yellow_box` and `red_box` based on position/color heuristics.
- **Current Limitation:** Lacks dedicated fine-tuned weights for the 8 specific flight experiment objects.
- **Potential Solution:** Annotate 500 frames from the raw BAS dataset in YOLO format and fine-tune YOLO11n on the custom classes (`yellow_box`, `red_box`, `container`, `inspection_pad`).
- **Difficulty:** Low.
- **Expected Impact:** Eliminates heuristic object mapping and achieves $>92\%$ mAP@50 on custom flight objects.
