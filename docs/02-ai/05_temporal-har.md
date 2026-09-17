# ORION Temporal Human Activity Recognition (ST-GCN)

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments (SIH26174)  
**Organization:** Indian Space Research Organisation (ISRO)  
**Date:** September 17, 2026  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. Mathematical Formulation of ST-GCN

The Spatial-Temporal Graph Convolutional Network (ST-GCN) models the human skeleton as an undirected spatial graph $G = (V, E)$ evolving across discrete time steps $t \in \{1, \dots, T\}$.

- **Nodes ($V=17$):** The 17 anatomical joints from the COCO skeleton topology.
- **Edges ($E$):** Physical skeletal bones (e.g., wrist-to-elbow, shoulder-to-neck, hip-to-knee).
- **Input Feature Map:** Tensor $X \in \mathbb{R}^{B \times C \times T \times V}$, where:
  - Batch size $B = 1$
  - Feature channels $C = 4$: $(x, y, \Delta x, \Delta y)$ where $\Delta x = x_t - x_{t-1}$ and $\Delta y = y_t - y_{t-1}$ encode instantaneous joint velocity vectors
  - Temporal window length $T = 32$ frames
  - Skeletal vertices $V = 17$ joints

---

## 2. Spatial Graph Partitioning & Convolution

To capture directional kinetic motion relative to the body core, the skeletal adjacency matrix $A$ is partitioned into 3 spatial subsets ($K=3$):

$$A + I = A_{root} + A_{centripetal} + A_{centrifugal}$$

1. **Root (Self):** The joint itself ($A_{root} = I$).
2. **Centripetal:** Neighboring joints that are closer to the body gravity center (midpoint of hips/shoulders).
3. **Centrifugal:** Neighboring joints that are farther from the body gravity center.

The spatial graph convolution at time step $t$ is expressed as:

$$f_{out} = \sum_{k=1}^{K} \Lambda_k^{-\frac{1}{2}} A_k \Lambda_k^{-\frac{1}{2}} f_{in} W_k$$

where $\Lambda_k^{ii} = \sum_j A_k^{ij} + \epsilon$ is the degree matrix, and $W_k$ is the learnable weight matrix for partition $k$.

---

## 3. Temporal Convolution & Receptive Field

Following the spatial graph convolution, a $1 \text{D}$ temporal convolution with kernel size $K_t = 9$ and stride 1 is applied along the temporal dimension $T$:

$$X_{t+1} = \text{ReLU}\left(\text{BatchNorm}\left(\text{Conv1D}_{9 \times 1}(X_t)\right)\right) + \text{Residual}(X_t)$$

The 9-layer ST-GCN network gradually reduces temporal resolution through strided convolutions while expanding channel dimensions ($64 \to 128 \to 256$), yielding a global temporal representation of the procedural movement.

---

## 4. Temporal Parameters & Window Coverage

Forensic audit of [`ActivityConfig`](file:///Users/amitkumar/Orion/ai/src/orion_ai/activity/configs.py) verifies the exact temporal parameters:

| Parameter | Configured Value | Temporal Coverage at 30 FPS | Operational Impact |
|---|---|---|---|
| **`window_size_frames`** | 32 frames | **1.067 seconds** | Captures complete micro-actions (e.g., reaching, grasping, unlatching, placing) without incorporating irrelevant past movements. |
| **`stride_frames`** | 8 frames | **0.267 seconds** | Downsamples forward inference rate; updates prediction ~3.75 times per second, maintaining responsive interactive guidance while keeping CPU usage minimal. |
| **`confidence_threshold`** | 0.65 | - | Rejects low-confidence predictions before routing to state machine. |
| **`smoothing_alpha`** | 0.70 | - | Exponential moving average parameter weighting recent inference heavily while suppressing single-frame noise. |
| **`max_entropy_threshold`**| 1.40 | - | Rejects multi-modal predictions where the model is split between conflicting classes. |
| **`debounce_threshold`** | 2 | ~0.53 seconds | Requires an action to be detected over two consecutive strides before triggering step advancement. |

---

## 5. Microgravity Invariance Transformation

Under microgravity conditions inside the space station, an astronaut's orientation can be inverted or tilted relative to the workstation camera. ORION applies a 2-step geometric normalization before the ST-GCN layer:

1. **Torso Translation Invariance:** The origin $(0, 0)$ is set to the midpoint between left hip (joint 11) and right hip (joint 12).
2. **Torso Scale Invariance:** Joint coordinates are divided by the torso length (Euclidean distance between neck/shoulders and hip midpoint).
This guarantees that changes in camera distance or astronaut bodily orientation do not distort the spatial-temporal graph topology.
