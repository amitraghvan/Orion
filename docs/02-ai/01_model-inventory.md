# ORION AI Model Inventory & Provenance

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments (SIH26174)  
**Organization:** Indian Space Research Organisation (ISRO)  
**Date:** September 17, 2026  
**Status:** FORENSICALLY VERIFIED AGAINST ON-DISK CHECKPOINTS  

---

## 1. Summary of Neural Network Models

| Model Identifier | Primary Task | Architecture | Checkpoint Path | File Size | Parameters | Status |
|---|---|---|---|---|---|---|
| **YOLO11n** | Object Detection | YOLO11 Nano CNN | [`models/weights/yolo11n.pt`](file:///Users/amitkumar/Orion/models/weights/yolo11n.pt) | 5.61 MB | ~2.6M | **REAL PRETRAINED MODEL** |
| **YOLO11n-pose** | Pose Estimation | YOLO11 Nano Pose | [`models/weights/yolo11n-pose.pt`](file:///Users/amitkumar/Orion/models/weights/yolo11n-pose.pt) | 6.25 MB | ~2.9M | **REAL PRETRAINED MODEL** |
| **ST-GCN HAR Baseline** | Temporal HAR | ST-GCN COCO-17 | [`models/weights/stgcn_har_v1.pt`](file:///Users/amitkumar/Orion/models/weights/stgcn_har_v1.pt) | 1.87 MB | 455,194 | **REAL TRAINED BASELINE** |
| **BAS-HAR Fine-Tuned** | BAS Experiment HAR | ST-GCN Interaction | [`models/bas_experiment/best.pt`](file:///Users/amitkumar/Orion/models/bas_experiment/best.pt) | 1.86 MB | 455,194 | **REAL FINE-TUNED MODEL** |

---

## 2. Model 1: Object Detection (`yolo11n.pt`)

- **Model Name:** Ultralytics YOLO11 Nano Object Detector
- **Architecture:** Convolutional backbone with C3k2 feature pyramid network and decoupled detection heads.
- **Framework:** PyTorch / TorchScript (Ultralytics v8.3+)
- **Checkpoint Location:** `models/weights/yolo11n.pt`
- **Manifest:** `models/weights/yolo11n.manifest.json`
- **File Size:** 5,613,764 bytes (5.61 MB)
- **SHA-256 Hash:** `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`
- **Input Shape:** $(B=1, C=3, H=640, W=640)$, normalized float32 $[0.0, 1.0]$.
- **Output Schema:** Anchor-free boxes $(x_1, y_1, x_2, y_2)$, confidence score, and class IDs across 80 COCO classes.
- **Classes:** 80 classes including `person`, `bottle`, `cup`, `bowl`, `chair`, `laptop`, `scissors`.
- **Inference Latency:**
  - Apple Silicon MPS: ~21.5 ms
  - Intel/Apple CPU: ~41.5 ms
- **License:** AGPL-3.0 (Recommended flight alternative: RT-DETR Apache 2.0 or ONNX export).
- **Status:** **REAL PRETRAINED MODEL (VERIFIED)**

---

## 3. Model 2: Pose Estimation (`yolo11n-pose.pt`)

- **Model Name:** Ultralytics YOLO11 Nano Pose Estimator
- **Architecture:** Single-stage bottom-up/top-down keypoint regression head over C3k2 backbone.
- **Framework:** PyTorch / TorchScript
- **Checkpoint Location:** `models/weights/yolo11n-pose.pt`
- **Manifest:** `models/weights/yolo11n-pose.manifest.json`
- **File Size:** 6,255,593 bytes (6.25 MB)
- **SHA-256 Hash:** `869e83fcdffdc7371fa4e34cd8e51c838cc729571d1635e5141e3075e9319dc0`
- **Input Shape:** $(B=1, C=3, H=640, W=640)$, normalized float32.
- **Keypoint Topology:** COCO 17 anatomical joints:
  0: Nose, 1: Left Eye, 2: Right Eye, 3: Left Ear, 4: Right Ear, 5: Left Shoulder, 6: Right Shoulder, 7: Left Elbow, 8: Right Elbow, 9: Left Wrist, 10: Right Wrist, 11: Left Hip, 12: Right Hip, 13: Left Knee, 14: Right Knee, 15: Left Ankle, 16: Right Ankle.
- **Output Schema:** Per-person bounding box + $(17 \times 3)$ tensor where each keypoint has $(x, y, \text{confidence})$.
- **Inference Latency:**
  - Apple Silicon MPS: ~22.8 ms
  - Intel/Apple CPU: ~44.1 ms
- **License:** AGPL-3.0.
- **Status:** **REAL PRETRAINED MODEL (VERIFIED)**

---

## 4. Model 3: Temporal HAR Baseline (`stgcn_har_v1.pt`)

- **Model Name:** Spatial-Temporal Graph Convolutional Network (ST-GCN Baseline)
- **Architecture:** 9-layer spatial-temporal graph convolutional blocks with residual skip connections and adaptive spatial partitioning.
- **Framework:** PyTorch
- **Checkpoint Location:** `models/weights/stgcn_har_v1.pt`
- **Manifest:** `models/weights/stgcn_har_v1.manifest.json`
- **File Size:** 1,869,845 bytes (1.87 MB)
- **SHA-256 Hash:** `41570e8d4471b6596abe459fd93c6f34546c0059d974e0629dc886451a3e95ed`
- **Parameters:** 455,194 trainable parameters.
- **Input Shape:** $(B=1, C=4, T=32, V=17)$, where $C=(x, y, \Delta x, \Delta y)$, $T=32$ frames, $V=17$ skeletal joints.
- **Output Classes (6):** `prepare_workstation`, `reach_tool`, `grasp_tool`, `manipulate_sample`, `inspect_chamber`, `idle`.
- **License:** Apache-2.0.
- **Status:** **REAL TRAINED BASELINE (VERIFIED)**

---

## 5. Model 4: BAS Fine-Tuned Model (`models/bas_experiment/best.pt`)

- **Model Name:** Fine-Tuned ST-GCN on BAS Spaceflight Experiment Data
- **Architecture:** `stgcn_coco17_interaction` (9 ST-GCN blocks with interaction channel modulation).
- **Framework:** PyTorch
- **Checkpoint Location:** `models/bas_experiment/best.pt` (Also `last.pt`)
- **Manifest:** `models/bas_experiment/model_manifest.json`
- **Metrics File:** `models/bas_experiment/metrics.json`
- **File Size:** 1,865,061 bytes (1.86 MB)
- **SHA-256 Hash:** `6d97fd61484bab97c978c5c946fbb7360a3574d00337faa3c4d62973d5f29b97`
- **Parameters:** 455,194 trainable parameters.
- **Input Shape:** $(B=1, C=4, T=32, V=17)$.
- **Output Classes (8):**
  1. `idle`
  2. `pick_yellow`
  3. `place_yellow`
  4. `pick_red`
  5. `place_red`
  6. `move_box`
  7. `check_box`
  8. `overlap_boxes`
- **Training Epochs:** 25 epochs (Batch size 16, learning rate 0.001 with cosine decay).
- **Training Duration:** 31.89 seconds.
- **Empirical Accuracy Metrics (from `metrics.json`):**
  - **Final Training Accuracy:** **95.56%** (Train Loss: 0.1475)
  - **Best Validation Accuracy:** **24.78%** (Epoch 20, Val Loss: 4.3135)
  - **Final Validation Accuracy:** **20.87%** (Epoch 25, Val Loss: 4.1907)
- **Inference Latency:**
  - Mean forward pass latency: **0.55 ms** (CPU)
- **Status:** **REAL FINE-TUNED MODEL (VERIFIED)**
- **Forensic Assessment:** The model trains and runs inference deterministically. However, due to the limited size of the initial dataset (20 video recordings), severe overfitting is observed between train (95.6%) and validation (24.8%). Dataset expansion is the primary path to production-level generalization.
