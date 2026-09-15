# ORION BAS AI Copilot — Phase 1.5 Architecture
**Project:** ORION — BAS AI Copilot (`orion-bas-ai`)  
**SIH Problem Statement:** SIH26174 (*AI Human Activity Recognition for On-board BAS Experiments*)  
**Phase:** 1.5 — Multimodal Human–Object Interaction & Microgravity-Aware Evidence Intelligence  
**Date:** September 2026  

---

## 1. System Overview

Phase 1.5 enriches the ORION perception engine with multimodal human–object interaction (HOI) intelligence. In microgravity payload operations (such as Biological Experiment Units aboard Gaganyaan / BAS), skeletal posture alone is ambiguous (e.g., reaching toward a rack looks identical whether a pipette, test tube, or glovebox latch is being grasped).

Phase 1.5 closes this gap by introducing:
1. **Pose-Seeded Hand Perception:** Extracting left and right hand bounding regions and wrist vectors from COCO-17 human skeletons.
2. **Target Object Perception & Tracking:** Detecting payload tools, containers, and apparatus with multi-class ByteTrack temporal consistency.
3. **Bipartite Hand–Object Association:** Deterministic bipartite matching using Hungarian optimization on microgravity-normalized Euclidean distance and bounding-box overlap.
4. **Temporal Hysteresis Interaction State Machine:** Tracking 7 distinct interaction phases (`NO_INTERACTION` ➔ `APPROACHING` ➔ `NEAR` ➔ `CONTACT` ➔ `GRASPING` ➔ `MANIPULATING` ➔ `RELEASING` ➔ `LOST`) with frame hysteresis to reject optical flicker and floating debris perturbations.
5. **Deterministic Multimodal Fusion:** Fusing ST-GCN temporal HAR predictions with physical grasp/manipulation evidence and object telemetry across 4 progressive fusion levels (L0–L3).
6. **Evidence Quality & Conflict Assessment:** Scoring evidence reliability and detecting modality discrepancies (e.g., ST-GCN predicts `grasp_tool` when no tool is present).

```
+---------------------------------------------------------------------------------------------------------+
|                                    PERCEPTION DAG (Phase 1.1 - 1.5)                                     |
|                                                                                                         |
|  [ Camera Frame Ingestion ]                                                                             |
|            |                                                                                            |
|            v                                                                                            |
|  +-------------------------+                                                                            |
|  | Person & Object Detect  |                                                                            |
|  | - YOLO11n Multi-Class   |                                                                            |
|  +-------------------------+                                                                            |
|       |               |                                                                                 |
|       | Persons       | Objects                                                                         |
|       v               v                                                                                 |
|  +-------------+  +----------------+                                                                    |
|  | Multi-Class |  | Object         |                                                                    |
|  | ByteTracker |  | ByteTracker    |                                                                    |
|  +-------------+  +----------------+                                                                    |
|       |                   |                                                                             |
|       v                   |                                                                             |
|  +-------------+          |                                                                             |
|  | YOLOPose    |          |                                                                             |
|  | Estimator   |          |                                                                             |
|  +-------------+          |                                                                             |
|       |                   |                                                                             |
|       v                   |                                                                             |
|  +-------------+          |                                                                             |
|  | Hungarian   |          |                                                                             |
|  | Pose-Track  |          |                                                                             |
|  +-------------+          |                                                                             |
|       |                   |                                                                             |
|       +-------------------+--------------------+                                                        |
|       |                                        |                                                        |
|       v                                        v                                                        |
|  +------------------------+             +-----------------------------+                                 |
|  | Pose-Based Hand        |             | ST-GCN Temporal HAR         |                                 |
|  | Region Extractor       |             | - 32-frame skeleton buffer  |                                 |
|  +------------------------+             | - Microgravity normalization|                                 |
|       |                                 | - 9-layer ST-GCN inference  |                                 |
|       v                                 +-----------------------------+                                 |
|  +---------------------------------------------+       |                                                |
|  | Hand-Object Associator (Hungarian matching) |       |                                                |
|  | - Invariant distance & bbox overlap         |       |                                                |
|  +---------------------------------------------+       |                                                |
|       |                                                |                                                |
|       v                                                |                                                |
|  +---------------------------------------------+       |                                                |
|  | Interaction State Machine (Hysteresis)      |       |                                                |
|  | - 7 states: APPROACHING -> GRASP -> MANIP   |       |                                                |
|  +---------------------------------------------+       |                                                |
|       |                                                |                                                |
|       +------------------------------------------------+                                                |
|       |                                                                                                 |
|       v                                                                                                 |
|  +--------------------------------------------------------------------+                                 |
|  | Deterministic Multimodal Fusion Engine                             |                                 |
|  | - Fusion Level 0: Skeletal only                                    |                                 |
|  | - Fusion Level 1: Object context augmented                         |                                 |
|  | - Fusion Level 2: Hand proximity augmented                        |                                 |
|  | - Fusion Level 3: Full Multimodal Interaction Fusion               |                                 |
|  | - Conflict Detector & Evidence Quality Scoring                     |                                 |
|  +--------------------------------------------------------------------+                                 |
|       |                                                                                                 |
|       v                                                                                                 |
|  [ StructuredObservation + ProtocolDecisionEngine + HUD Telemetry ]                                     |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. Component Specifications

### 2.1 Pose-Seeded Hand Extractor (`ai/src/orion_ai/hand/`)
- Utilizes COCO-17 wrist joints (`Keypoint 9: left_wrist`, `Keypoint 10: right_wrist`) and parent elbow joints (`Keypoint 7`, `Keypoint 8`) to establish wrist approach vectors.
- Defines localized hand bounding boxes sized proportionally to the astronaut's bounding box diagonal, ensuring scale invariance regardless of camera zoom or distance.
- Tracks hand visibility state: `OBSERVED`, `OCCLUDED`, `INFERRED`, or `MISSING`.

### 2.2 Microgravity-Invariant Spatial Geometry (`ai/src/orion_ai/interaction/geometry.py`)
- Standardizes Euclidean distances by dividing by the actor's torso or bounding box diagonal:
  $$d_{\text{norm}} = \frac{\|\mathbf{c}_{\text{hand}} - \mathbf{c}_{\text{obj}}\|}{D_{\text{reference}}}$$
- Computes asymmetric intersection-over-union (IoU) and overlap ratios:
  $$\text{Overlap}(\text{Hand}, \text{Object}) = \frac{\text{Area}(\text{Hand} \cap \text{Object})}{\min(\text{Area}(\text{Hand}), \text{Area}(\text{Object}))}$$
- Calculates approach velocity as the delta of normalized distance over consecutive frames:
  $$v_{\text{approach}} = d_{\text{norm}}(t-1) - d_{\text{norm}}(t)$$

### 2.3 Hand–Object Associator (`ai/src/orion_ai/interaction/hand_object_associator.py`)
- Constructs an $N \times M$ cost matrix pairing $N$ active hands to $M$ detected objects:
  $$C_{i,j} = d_{\text{norm}}(i, j) - 0.5 \cdot \text{Overlap}(i, j)$$
- Solves global minimum cost assignment via `scipy.optimize.linear_sum_assignment`.
- Rejects pairings exceeding the maximum association distance threshold ($d_{\text{norm}} > 0.50$).

### 2.4 Interaction State Machine (`ai/src/orion_ai/interaction/state_machine.py`)
- Implements temporal hysteresis across 7 interaction states:
  1. `NO_INTERACTION`: Hand is distant ($d_{\text{norm}} > 0.35$).
  2. `NEAR`: Hand is proximate ($d_{\text{norm}} \le 0.35$).
  3. `APPROACHING`: Hand is proximate and moving toward the object ($v_{\text{approach}} > 0.005$) for $\ge 2$ consecutive frames.
  4. `CONTACT`: Hand overlaps or directly touches object ($d_{\text{norm}} \le 0.05$ or $\text{Overlap} \ge 0.10$).
  5. `GRASPING`: Sustained contact persisting for $\ge 3$ consecutive frames.
  6. `MANIPULATING`: Sustained grasp accompanied by correlated hand-object motion vectors for $\ge 2$ frames.
  7. `RELEASING`: Contact broken following a grasp or manipulation phase.
- Prevents single-frame optical dropouts or transient contact from triggering step completion.

### 2.5 Deterministic Multimodal Fusion (`ai/src/orion_ai/interaction/fusion.py`)
- Combines neural ST-GCN predictions with physical HOI telemetry:
  - **Level 0 (Kinematic Baseline):** Returns raw ST-GCN activity prediction.
  - **Level 1 (Object-Aware):** Validates that predicted activity targets (e.g. `pipette`) correspond to an observed object in the scene.
  - **Level 2 (Hand-Aware):** Enforces that astronaut hands are actively deployed in proximity to the experiment apparatus.
  - **Level 3 (Full Multimodal Fusion):** Requires concurrence between ST-GCN posture and physical interaction state (`GRASPING` or `MANIPULATING`). Boosts decision confidence when modalities agree, and flags `CONFLICTING_EVIDENCE` when ST-GCN predicts interaction on non-existent or uncontacted tools.

### 2.6 Evidence Quality Assessor (`ai/src/orion_ai/interaction/evidence_quality.py`)
- Computes a unified composite quality score $Q \in [0.0, 1.0]$:
  $$Q = w_{\text{pose}} \cdot C_{\text{pose}} + w_{\text{hand}} \cdot C_{\text{hand}} + w_{\text{obj}} \cdot C_{\text{obj}} + w_{\text{hoi}} \cdot C_{\text{hoi}}$$
- Categorizes observations into `HIGH`, `MEDIUM`, `LOW`, or `DEGRADED`, driving protocol step validation gating.

---

## 3. Real-Time Telemetry & Cockpit HUD

The React/Vite Cockpit HUD displays:
- Real-time overlay of detected tools and sample containers with bounding boxes and class badges.
- Wrist-to-object interaction vectors drawn on the canvas with color-coded state indicators (Cyan = Approaching, Yellow = Contact, Green = Grasping, Emerald = Manipulating).
- Multimodal Interaction HUD card displaying active actor, target object, interaction state, contact persistence, evidence quality rating, and conflict warning alerts.
