# Architectural Decision Record (ADR) 006: ST-GCN Temporal Action Recognition Architecture

## Status
**ACCEPTED** (2026-09-08)

## Context
Phase 1.2 established real-time object detection and 17-keypoint skeleton pose estimation. However, human activity recognition in microgravity requires temporal sequence modeling over multiple consecutive frames. Alternatives considered include:
1. **Raw Video 3D CNNs (e.g., SlowFast, I3D, Video Swin)**: Heavy compute footprint (> 50M parameters, > 100 ms latency on CPU/edge TPU), sensitive to glovebox lighting and background changes, and difficult to deploy under strict aerospace thermal budgets.
2. **Naive MLP / LSTM over flattened coordinates**: Disregards human anatomical bone topology and spatial kinematic hierarchies.
3. **Spatial-Temporal Graph Convolutional Networks (ST-GCN)**: Directly models the human skeleton as an anatomical graph ($V=17$ nodes) with spatial graph convolutions and temporal 1D convolutions. Extremely lightweight (~250k parameters, < 5 ms CPU forward pass), robust to camera framing and glovebox illumination.

## Decision
1. Implement a standalone PyTorch ST-GCN model operating on 17-keypoint COCO skeleton graphs.
2. Structure the network into 4 residual ST-GCN blocks with learnable edge importance weighting ($A \odot M$).
3. Limit the model to 6 trained activity classes (`prepare_workstation`, `reach_tool`, `grasp_tool`, `manipulate_sample`, `inspect_chamber`, `idle`).
4. Handle epistemic uncertainty (`UNKNOWN`, `UNCERTAIN`, `WARMING_UP`, `DEGRADED`) outside the neural network in the `UncertaintyEvaluator`.

## Consequences
- **Positive**: Low memory and computational overhead suitable for air-gapped spaceflight hardware. Topological invariance across camera viewpoints.
- **Negative**: Relies on reliable upstream pose estimation; keypoint detection failures degrade classification accuracy if not explicitly handled.
