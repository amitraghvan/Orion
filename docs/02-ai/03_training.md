# ORION AI Training & Evaluation Pipeline

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments (SIH26174)  
**Organization:** Indian Space Research Organisation (ISRO)  
**Date:** September 17, 2026  
**Status:** IMPLEMENTED, EXECUTED & FORENSICALLY DOCUMENTED  

---

## 1. Training Pipeline Architecture

The end-to-end training pipeline ingests raw experiment videos, extracts skeletal joint sequences and bounding boxes, formats spatial-temporal tensors, and trains the Spatial-Temporal Graph Convolutional Network (ST-GCN):

```
Raw BAS Experiment MP4 Videos (datasets/bas_experiment/raw/)
                        │
                        ▼
[Feature Extraction: scripts/prepare_bas_dataset.py]
  - YOLO11n-pose keypoint regression (17 joints)
  - YOLO11n object detection & ByteTrack tracking
  - Hand extraction via wrist/elbow geometry
  - Microgravity torso-relative normalization
                        │
                        ▼
Structured Kinematic Sequences (datasets/bas_experiment/sequences/)
                        │
                        ▼
[Training Execution: scripts/train_bas_har.py]
  - Architecture: ST-GCN (stgcn_coco17_interaction)
  - Loss: CrossEntropyLoss with Label Smoothing
  - Optimizer: AdamW with Cosine Annealing LR schedule
  - Epochs: 25 | Batch Size: 16
                        │
                        ▼
Trained Checkpoints (models/bas_experiment/best.pt, last.pt)
                        │
                        ▼
[Model Evaluation: scripts/evaluate_bas_har.py]
  - Validation metrics (metrics.json)
  - Confusion Matrix (confusion_matrix.png)
```

---

## 2. Verified Execution Commands

All training and evaluation workflows are fully reproducible using the scripts in `scripts/`:

### Step 1: Ingest and Prepare Dataset
```bash
# Extract skeletal joints, normalize coordinates, and generate sequence annotations
python scripts/prepare_bas_dataset.py \
    --raw-dir datasets/bas_experiment/raw \
    --output-dir datasets/bas_experiment/sequences \
    --device mps
```

### Step 2: Validate Dataset Quality
```bash
# Audit annotations, check for missing frames, and verify sequence lengths
python scripts/validate_bas_dataset.py --dataset-dir datasets/bas_experiment
```

### Step 3: Train Spatial-Temporal Graph Convolutional Network
```bash
# Fine-tune ST-GCN on BAS experiment sequences
python scripts/train_bas_har.py \
    --data-dir datasets/bas_experiment/sequences \
    --output-dir models/bas_experiment \
    --epochs 25 \
    --batch-size 16 \
    --lr 0.001 \
    --device mps
```

### Step 4: Evaluate Model Checkpoint
```bash
# Compute per-class accuracy, macro F1 score, and confusion matrix
python scripts/evaluate_bas_har.py \
    --model-path models/bas_experiment/best.pt \
    --data-dir datasets/bas_experiment/sequences \
    --output-dir models/bas_experiment
```

---

## 3. Empirical Training Results (Forensic Verification)

From [`models/bas_experiment/metrics.json`](file:///Users/amitkumar/Orion/models/bas_experiment/metrics.json):

- **Model Identifier:** `BAS-HAR-v1.0`
- **Architecture:** `stgcn_coco17_interaction` ($C=4, T=32, V=17$, 8 classes)
- **Epochs Completed:** 25
- **Batch Size:** 16
- **Total Training Wall Time:** 31.89 seconds (Apple Silicon MPS)
- **Train Accuracy:** **95.56%** (Train Loss: 0.1475)
- **Best Validation Accuracy:** **24.78%** (Epoch 20, Val Loss: 4.3135)
- **Final Validation Accuracy:** **20.87%** (Epoch 25, Val Loss: 4.1907)
- **Best Checkpoint SHA-256:** `6d97fd61484bab97c978c5c946fbb7360a3574d00337faa3c4d62973d5f29b97`

### Loss and Accuracy Trajectory Across 25 Epochs:

| Epoch | Train Loss | Train Acc | Val Loss | Val Acc | Learning Rate |
|---|---|---|---|---|---|
| 1 | 1.4979 | 43.34% | 2.5478 | 12.61% | 0.000996 |
| 5 | 0.6391 | 77.80% | 4.6673 | 6.96% | 0.000905 |
| 10 | 0.3308 | 89.01% | 3.8479 | 10.87% | 0.000658 |
| 15 | 0.2857 | 91.97% | 4.2756 | 19.13% | 0.000352 |
| 20 | 0.1449 | 95.56% | 4.3135 | **24.78%** | 0.000105 |
| 25 | 0.1475 | 95.56% | 4.1907 | 20.87% | 0.000010 |

---

## 4. Scientific Analysis of Generalization Gap

### Why is Validation Accuracy 24.78% while Training Accuracy is 95.56%?
1. **Sample Diversity:** The dataset currently has 20 raw video files. With an 8-class classification task, this equates to roughly 2-3 unique physical video executions per class.
2. **Subject Independence:** The validation split is held out on Subject `SP04`. Different astronauts exhibit distinct movement cadences, arm spans, and reaching angles.
3. **Data Scarcity Overfitting:** A deep neural network with 455,194 parameters easily memorizes kinematic trajectories of 15 training videos.
4. **Remediation Strategy:** Synthetic kinetic trajectory augmentation (rotation jitter, temporal warping, velocity scaling) combined with collecting 200+ video sequences across more subjects will bring validation accuracy to flight standards ($>85\%$).
