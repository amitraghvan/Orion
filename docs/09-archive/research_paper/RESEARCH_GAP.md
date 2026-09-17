# SCIENTIFIC RESEARCH GAP, QUESTIONS & HYPOTHESES: ORION
**Document ID:** ORION-GAP-2026-005  
**Classification:** Research Foundation & Literature Review  
**Date:** September 2026  
**Repository Path:** `/Users/amitkumar/Orion`  
**SIH Problem Statement:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments  

---

## 1. Systematic Related Work Analysis

Human Activity Recognition (HAR) and procedural workflow validation have evolved across distinct, often disconnected disciplines in computer vision and artificial intelligence:

### 1.1 Skeleton-Based Human Action Recognition
- **Foundational Works:** Yan et al. (AAAI 2018) pioneered Spatio-Temporal Graph Convolutional Networks (ST-GCN), formulating human skeletons as non-Euclidean graphs where vertices represent joints and edges represent physical bones. Shi et al. (CVPR 2019) introduced Two-Stream Adaptive Graph Convolutional Networks (2s-AGCN), and Chen et al. (ICCV 2021) developed Channel-Wise Topology Refinement GCN (CTR-GCN).
- **Benchmarking Datasets:** NTU-RGB+D (Shahroudy et al., CVPR 2016), NTU-RGB+D 120 (Liu et al., TPAMI 2019), and Kinetics-Skeleton (Carreira & Zisserman, CVPR 2017).
- **Inherent Limitation:** These models are evaluated on vast, balanced datasets ($10^4$ to $10^5$ samples) featuring hundreds of human subjects. When transferred to specialized aerospace domains with extreme small-sample constraints ($N \le 4$ subjects), pure GCNs experience severe feature collapse across unseen subjects due to inter-individual kinematic and morphological variance.

### 1.2 Procedural & Workflow Action Recognition
- **Key Benchmarks:** Breakfast Actions Dataset (Kuehne et al., CVPR 2014), COIN (Tang et al., CVPR 2019), Epic-Kitchens (Damen et al., IJCV 2022), Ego4D (Grauman et al., CVPR 2022), and Assembly101 (Sener et al., CVPR 2022).
- **Methodology:** Typically relies on heavy temporal action segmentation networks (e.g. MS-TCN, Farha & Gall, CVPR 2019; ASFormer, Yi et al., BMVC 2021) or multimodal transformers trained on thousands of hours of video.
- **Inherent Limitation:** Existing procedural models focus on *post-hoc* offline video segmentation. They lack real-time, low-latency step-by-step guidance, do not enforce deterministic safety invariants, and cannot run within the constrained 15–30W edge compute envelope of an aerospace scientific module.

### 1.3 Hand-Object Interaction (HOI) Detection
- **Key Approaches:** Chao et al. (WACV 2018), Qi et al. (ECCV 2018), and transformer-based HOI (Tamura et al., CVPR 2021; Zhang et al., CVPR 2021).
- **Inherent Limitation:** Standard HOI networks operate frame-by-frame without temporal state hysteresis. In microgravity or glovebox environments, momentary visual occlusions cause severe flicker. Furthermore, dual-network architectures (e.g. running YOLO + MediaPipe Hands + HOI-Transformer) introduce 50–100 ms of latency, exceeding edge compute budgets.

### 1.4 Edge AI & Constrained Offline Perception
- **Aerospace & Edge Context:** Space stations (ISS, Tiangong, and the upcoming Bharatiya Antariksh Station) operate with highly restricted communications bandwidth and intermittent ground contact. Local payload monitoring must operate completely air-gapped without cloud APIs.
- **Inherent Limitation:** The vast majority of modern Vision-Language-Action (VLA) models and multimodal assistants (e.g. GPT-4V, Gemini Pro, LLaVA) require remote server farms, rendering them fundamentally unviable for autonomous spaceflight operations.

---

## 2. Identified Research Gaps

| Research Dimension | Existing Literature Approach | Literature Limitation | ORION Architectural Solution |
| :--- | :--- | :--- | :--- |
| **Procedural Context** | Classifies isolated action snippets ($A_t$). | Does not evaluate whether action is permissible at step $S_k$. | 11-State Procedural FSM validating $P_{t+1} = \mathcal{F}(P_t, O_t, A_t, I_t)$. |
| **Sample Size Robustness** | Deep neural models trained on $N \ge 100$ subjects. | Catastrophic accuracy drop ($< 5\%$) on unseen subjects when $N \le 4$. | Hybrid Neuro-Symbolic defense coupling GCN priors with deterministic object grounding. |
| **Hand Perception Overhead** | Secondary 21-keypoint hand networks (e.g. MediaPipe). | Incurs 15–25 ms latency; violates 30 FPS edge budget. | Zero-latency kinematic extraction from COCO wrists ($0$ extra forward passes). |
| **Uncertainty & Safety** | Raw softmax probabilities with arbitrary thresholds. | False alarms triggered by transient noise ($UNKNOWN \to \text{Violation}$). | Formal safety invariants: $UNKNOWN \ne WRONG$, $UNCERTAIN \ne VIOLATION$. |
| **Connectivity & Bandwidth**| Cloud-tethered VLMs or heavy server GPUs. | Cannot function under air-gapped spaceflight constraints. | Fully local edge pipeline achieving 12.8–14.1 FPS on CPU, ~37 FPS on MPS. |

---

## 3. Formal Research Questions (RQs)

To guide the scientific evaluation of ORION, five formal research questions are formulated:

- **RQ1 (Multimodal Robustness):** Can multimodal perception combining skeletal pose, spatial object detection, and hand-object proximity compensate for neural classification collapse in extreme small-sample domain regimes ($N=4$)?
- **RQ2 (Deterministic Sequence Validation):** Can a confidence-calibrated, 11-state procedural finite state machine reliably detect procedural violations (wrong object, out-of-order execution, skipped steps) with zero false alarms on valid sequences?
- **RQ3 (Zero-Latency Hand Perception):** Can kinematic hand extraction derived directly from skeletal wrist keypoints provide sufficient spatial precision for hand-object association without invoking an auxiliary neural network?
- **RQ4 (Edge Real-Time Feasibility):** Can an integrated perception DAG (YOLO detection, pose estimation, ByteTrack, ST-GCN, and FSM) achieve near-real-time throughput ($\ge 12$ FPS) under constrained CPU/edge compute without cloud assistance?
- **RQ5 (Neuro-Symbolic Explainability):** Does decoupling probabilistic perception from deterministic procedural validation provide an interpretable audit trail that explains *why* an action was accepted or flagged as a violation?

---

## 4. Testable Scientific Hypotheses

- **Hypothesis 1 (H1 — Multimodal Defense):** In small-$N$ domains where pure kinematic graph convolutions fail to generalize across unseen human morphologies, coupling neural temporal priors with deterministic chromatic object grounding will yield $\ge 95\%$ protocol violation detection.
- **Hypothesis 2 (H2 — Invariant Safety):** Enforcing formal safety invariants ($UNKNOWN \ne WRONG$, $UNCERTAIN \ne VIOLATION$) alongside temporal debouncing ($K=2$ windows) will reduce false violation alarms on valid sequences to $\le 1.0\%$.
- **Hypothesis 3 (H3 — Computational Sizing):** Slicing hand regions from upper-limb skeletal keypoints and amortizing ST-GCN inference via an 8-frame sliding window stride will maintain end-to-end processing latency under 80 ms on commodity ARM/x86 CPUs.
- **Hypothesis 4 (H4 — Procedural Decoupling):** Evaluating protocol validity via a deterministic state transition function $P_{t+1} = \mathcal{F}(P_t, O_t, A_t, I_t)$ produces an immutable evidence structure that unambiguously attributes procedural deviations to specific physical objects or step ordering errors.
