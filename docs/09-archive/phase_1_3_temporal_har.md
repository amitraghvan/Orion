# ORION — BAS AI Copilot (SIH26174)
# Phase 1.3 Technical Deep-Dive: Spatial-Temporal Graph Convolutional Networks (ST-GCN)

---

## 1. Mathematical Formulation

### 1.1 Skeleton Graph Topology
Let $G = (V, E)$ represent the human skeleton graph with $N = 17$ keypoint vertices (COCO topology):
- $V = \{v_1, v_2, \dots, v_{17}\}$
- $E = \{(v_i, v_j) \mid \text{anatomical bone between } i \text{ and } j\} \cup \{(v_i, v_i)\}$

Bone connectivity:
- Head: $(0, 1), (0, 2), (1, 3), (2, 4)$
- Upper Body: $(5, 6), (5, 7), (7, 9), (6, 8), (8, 10)$
- Torso: $(5, 11), (6, 12), (11, 12)$
- Lower Body: $(11, 13), (13, 15), (12, 14), (14, 16)$

### 1.2 Spatial Graph Partitioning
Following Yan et al. (*Spatial Temporal Graph Convolutional Networks for Skeleton-Based Action Recognition*, AAAI 2018), the neighbor set $B(v_i)$ is partitioned into $K_v = 3$ subsets:
1. **Root node (subset 0)**: $v_i$ itself.
2. **Centripetal / Inward group (subset 1)**: Neighboring joints closer to the skeleton gravity center (mid-hip).
3. **Centrifugal / Outward group (subset 2)**: Neighboring joints farther from the gravity center.

The spatial graph convolution on feature map $X_{\text{in}} \in \mathbb{R}^{C_{\text{in}} \times T \times V}$ is expressed as:
$$X_{\text{out}} = \sum_{k=0}^{K_v - 1} W_k \left( X_{\text{in}} (A_k \odot M_k) \right)$$
where:
- $A_k \in \mathbb{R}^{V \times V}$ is the normalized adjacency matrix for partition $k$.
- $M_k \in \mathbb{R}^{V \times V}$ is a learnable edge importance weight mask initialized to ones.
- $W_k \in \mathbb{R}^{C_{\text{out}} \times C_{\text{in}} \times 1 \times 1}$ is the $1 \times 1$ spatial convolution weight tensor.

### 1.3 Temporal Convolution
Temporal modeling applies standard 2D convolutions with kernel size $K_t \times 1$ (default $K_t = 9$) across the time dimension $T$, followed by Batch Normalization, ReLU activation, and Dropout.

A residual connection is applied around each spatial-temporal block:
$$Y = \text{ST-GCN}(X) + \text{Residual}(X)$$

---

## 2. Activity Taxonomy

### 2.1 Trained Model Classes (6)
1. `prepare_workstation` (Macro/procedural preparation action)
2. `reach_tool` (Atomic reaching motion toward tool / rack)
3. `grasp_tool` (Atomic grasping of pipette, vial, or glovebox tool)
4. `manipulate_sample` (Atomic fine-manipulation, pipetting, or injection)
5. `inspect_chamber` (Atomic visual verification of growth cassette)
6. `idle` (Passive floating / standing without active manipulation)

### 2.2 Epistemic Runtime Evaluation States (5)
1. `NOMINAL`: Top-1 probability $\ge 0.60$ and margin over top-2 $\ge 0.15$.
2. `UNKNOWN`: Top-1 probability $< 0.60$ (unrecognized motion pattern).
3. `UNCERTAIN`: Top-1 vs top-2 probability difference $< 0.15$ (ambiguous classifier output).
4. `WARMING_UP`: Temporal sequence length $N < T$ (buffer filling).
5. `DEGRADED`: Checkpoint missing, corrupted, or runtime failure isolated.

---

## 3. Microgravity-Motivated Normalization Pipeline

Given raw keypoint coordinates $(x_i, y_i)$ with optical frame width $W$ and height $H$:

```
Raw BGR Frame (640x480)
       │
       ▼
Pose Keypoint Detection: (u_i, v_i) in [0, 640] x [0, 480]
       │
       ▼
Canonical Image Space:
  P_i = ((u_i - W/2) / max(W, H), (v_i - H/2) / max(W, H))
       │
       ▼
Mid-Hip Root Centering:
  P_root = 0.5 * (P_11 + P_12)
  P_centered,i = P_i - P_root
       │
       ▼
Trunk Scale Normalization:
  P_shoulder = 0.5 * (P_5 + P_6)
  s = ||P_shoulder - P_root||_2
  s_safe = max(s, epsilon)  [epsilon = 1e-4]
  P_norm,i = P_centered,i / s_safe
       │
       ▼
Velocity Feature Generation:
  V_i,t = P_norm,i,t - P_norm,i,t-1
       │
       ▼
Input Tensor (C=4, T, V=17) [x_norm, y_norm, v_x, v_y]
```

---

## 4. Keypoint Reliability Tracking

Rather than blindly interpolating missing keypoints, each joint in the temporal buffer tracks its state:
- `OBSERVED`: Detected with confidence $\ge 0.20$.
- `INTERPOLATED`: Missing for $\le 2$ frames. Linear interpolation applied; confidence scaled by $0.60$.
- `HELD`: Missing for 3 frames. Last known position held; confidence scaled to $0.35$.
- `INVALID`: Missing for $> 3$ frames. Joint coordinate set to zero; confidence $= 0.0$.
