# ORION AI & Computer Vision Pipeline Audit

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments (SIH26174)  
**Organization:** Indian Space Research Organisation (ISRO)  
**Date:** September 17, 2026  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. Executive Summary & Nature of the AI System

### Is this actually Human Activity Recognition?
**Yes.** ORION executes genuine deep-learning-based Human Activity Recognition (HAR), combined with human-object interaction (HOI) perception and rule-based protocol state validation.

Specifically, ORION implements a **hybrid multimodal architecture**:
1. **Spatial Representation:** Deep convolutional object detection (YOLO11n) and 17-keypoint human pose estimation (YOLO11n-pose).
2. **Temporal Modeling:** A dedicated Spatial-Temporal Graph Convolutional Network (**ST-GCN**) operating on sliding temporal windows of 32 skeleton frames ($T=32$, $V=17$, $C=4$).
3. **Multimodal Interaction:** Geometric hand-object interaction (HOI) modeling tracking contact states (`APPROACH`, `TOUCH`, `MANIPULATE`, `RELEASE`).
4. **Sequence Verification:** A deterministic protocol decision engine that enforces safety invariants, debouncing, and out-of-order detection over the recognized activities.

It is **NOT** a naive heuristic or single-frame classification system. It explicitly models the spatial graph of the human body and the temporal dynamics across time.

---

## 2. Stage-by-Stage Perception Pipeline

```
[1. Camera Ingestion]
         │
         ▼
[2. Frame Preprocessing]
         │
         ├──► [3. Object Detection (YOLO11n)]
         │           │
         │           ▼
         │    [4. Multi-Class Tracking (ByteTrack)]
         │           │
         └──► [5. Pose Estimation (YOLO11n-pose)]
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
[6. Hand Extraction]    [8. Temporal Skeleton Buffer]
         │                       │
         ▼                       ▼
[7. Hand-Object (HOI)]  [9. ST-GCN HAR Inference]
         │                       │
         └───────────┬───────────┘
                     ▼
        [10. Multimodal Fusion & Smoothing]
                     │
                     ▼
        [11. Activity Classification]
                     │
                     ▼
        [12. Protocol Step Mapping]
                     │
                     ▼
        [13. Sequence Validation & Debouncing]
                     │
                     ▼
        [14. Confidence & Entropy Gating]
                     │
                     ▼
        [15. Canonical Event Generation]
```

---

### Stage 1: Camera Ingestion
- **Input:** Hardware video stream (CSI camera, USB webcam, or MP4 video file).
- **Processing:** `LiveCameraSource` uses OpenCV `VideoCapture` running in a dedicated OS thread. Reads frames into a thread-safe `FrameBuffer` (bounded ring buffer with `maxlen=2`).
- **Model:** None (Hardware driver / OpenCV API).
- **Output:** BGR `numpy.ndarray` frame ($1280 \times 720$ or $640 \times 480$, uint8), `frame_id`, and monotonic `timestamp`.
- **Next Stage:** Frame Preprocessing.

### Stage 2: Frame Preprocessing
- **Input:** Raw BGR video frame.
- **Processing:** Letterbox resizing to $640 \times 640$ keeping aspect ratio, normalization from $[0, 255]$ to $[0.0, 1.0]$, and conversion to PyTorch Tensor format $(1, 3, 640, 640)$ on the active accelerator (`mps`, `cuda`, or `cpu`).
- **Model:** Native C++ SIMD routines in `orion_native` or OpenCV `cv2.resize`.
- **Output:** Preprocessed Tensor.
- **Next Stage:** Parallel Object Detection and Pose Estimation.

### Stage 3: Object Detection
- **Input:** Preprocessed frame tensor $(1, 3, 640, 640)$.
- **Processing:** Forward pass through deep convolutional network. Computes anchor-free bounding box coordinates, class scores, and non-maximum suppression (NMS) with IoU threshold 0.45.
- **Model:** Ultralytics YOLO11n (`models/weights/yolo11n.pt`, 5.61 MB, 80 COCO classes).
- **Output:** List of candidate detections with $[x_1, y_1, x_2, y_2]$, confidence score $\ge 0.25$, and class labels (person, tools, bottles, containers).
- **Next Stage:** Object Tracking.

### Stage 4: Multi-Class Object Tracking
- **Input:** Raw object detections from Stage 3.
- **Processing:** Bipartite matching with Kalman filter prediction. Re-identifies objects across frames and assigns consistent `track_id` values. Separates high-confidence matches from low-confidence recovery.
- **Model:** Multi-class `ByteTracker` (`ai/src/orion_ai/tracking/byte_tracker.py`).
- **Output:** Tracked objects with persistent track IDs, bounding boxes, and velocity vectors.
- **Next Stage:** Hand-Object Interaction Engine.

### Stage 5: Pose Estimation
- **Input:** Preprocessed frame tensor $(1, 3, 640, 640)$.
- **Processing:** Top-down/single-stage keypoint estimation predicting 17 anatomical landmarks per human subject.
- **Model:** YOLO11n-pose (`models/weights/yolo11n-pose.pt`, 6.25 MB).
- **Output:** 17 keypoints per person $(x, y, c)$ representing: Nose, Eyes, Ears, Shoulders, Elbows, Wrists, Hips, Knees, and Ankles.
- **Next Stage:** Hand Extraction and Temporal HAR Buffering.

### Stage 6: Hand Perception & Extraction
- **Input:** 17-keypoint skeleton detections.
- **Processing:** Extracts left wrist (keypoint 9) and right wrist (keypoint 10). Employs geometric limb vector expansion using elbows (keypoints 7, 8) to calculate hand bounding boxes and hand center coordinates $[w_x, w_y]$.
- **Model:** Geometric rule-based extractor (`ai/src/orion_ai/hand/extractor.py`).
- **Output:** Hand detections with `hand_id`, side (`left` / `right`), bounding box, center, and joint confidence.
- **Next Stage:** Hand-Object Interaction (HOI).

### Stage 7: Hand-Object Interaction (HOI) Modeling
- **Input:** Extracted hands (Stage 6) and tracked experiment objects (Stage 4).
- **Processing:** Calculates pairwise Euclidean distances and bounding box Intersection-over-Union (IoU). Evaluates temporal contact transitions:
  - $\text{dist} > 120\text{px} \implies \text{IDLE}$
  - $\text{dist} \le 120\text{px} \implies \text{APPROACH}$
  - $\text{dist} \le 72\text{px} \implies \text{TOUCH}$
  - $\text{IoU} > 0.15 \implies \text{MANIPULATE}$
- **Model:** HOI Contact State Machine (`ai/src/orion_ai/interaction/state_machine.py`).
- **Output:** Interaction triplets: `(Astronaut, Action, Target_Object)` with contact state and confidence.
- **Next Stage:** Multimodal Fusion & Step Mapping.

### Stage 8: Temporal Skeleton Buffering
- **Input:** Primary subject 17-keypoint skeletal coordinates.
- **Processing:** Normalizes keypoints relative to torso center (midpoint of hips and shoulders) to achieve translation and scale invariance under zero-gravity conditions. Stores coordinates in a sliding window buffer of length $T=32$ frames.
- **Model:** `TemporalFeatureBuffer` (`ai/src/orion_ai/activity/buffer.py`).
- **Output:** Spatial-temporal tensor of shape $(B=1, C=4, T=32, V=17)$, where $C=(x, y, \Delta x, \Delta y)$.
- **Next Stage:** ST-GCN HAR Inference.

### Stage 9: ST-GCN HAR Inference
- **Input:** Temporal skeleton tensor $(1, 4, 32, 17)$.
- **Processing:** Executes multi-scale spatial graph convolutions along skeletal adjacency partitions (Centripetal, Centrifugal, Self) combined with 1D temporal convolutions along time. Forward pass is executed every 8 frames (stride = 8).
- **Model:** ST-GCN (`models/bas_experiment/best.pt` or `models/weights/stgcn_har_v1.pt`, 455,194 parameters).
- **Output:** Logit vector over action classes (`pick_yellow`, `place_yellow`, `pick_red`, `place_red`, `move_box`, `check_box`, `overlap_boxes`, `idle`).
- **Next Stage:** Temporal Smoothing.

### Stage 10: Temporal Smoothing & Uncertainty Calibration
- **Input:** Raw logits from ST-GCN.
- **Processing:**
  1. Softmax normalization: $P_k = \frac{e^{z_k}}{\sum_j e^{z_j}}$.
  2. Exponential moving average (EMA) smoothing across sliding inference steps: $S_t = \alpha P_t + (1 - \alpha) S_{t-1}$ ($\alpha = 0.7$).
  3. Shannon entropy calculation: $H(P) = -\sum_{k} P_k \ln(P_k)$.
  4. Uncertainty classification:
     - $H \le 1.00 \implies \text{NOMINAL}$
     - $1.00 < H \le 1.40 \implies \text{MARGINAL}$
     - $H > 1.40 \implies \text{UNCERTAIN}$ (Prediction suppressed)
- **Model:** `TemporalPredictionSmoother` & `UncertaintyEvaluator` (`ai/src/orion_ai/activity/smoothing.py`).
- **Output:** Smoothed action label, calibrated confidence, entropy score, and uncertainty status.
- **Next Stage:** Activity Classification.

### Stage 11: Activity Classification & Step Mapping
- **Input:** Smoothed action label, HOI contact state, and target object class.
- **Processing:** Maps fine-grained physical movements to canonical protocol action tokens via `ActionMapper`. For example, manipulating the red container maps to `pick_red` or `place_red`.
- **Model:** `ActionMapper` (`app/intelligence/decision_engine.py`).
- **Output:** Canonical action token.
- **Next Stage:** Sequence Validation.

### Stage 12: Sequence Validation & Safety Enforcement
- **Input:** Canonical action token, confidence, entropy, and active protocol specification.
- **Processing:** Evaluates observation against the active step's expected action set:
  - If action matches active step and debounce count $\ge 2 \implies \text{VALID}$
  - If action matches a future protocol step $\implies \text{OUT\_OF\_SEQUENCE}$ (Identifies skipped steps)
  - If action manipulates wrong colored object $\implies \text{WRONG\_OBJECT}$
  - If confidence $< 0.65$ or entropy $> 1.40 \implies \text{STEP\_UNCERTAIN}$
- **Model:** `ProtocolDecisionEngine` (`app/intelligence/decision_engine.py`).
- **Output:** `ProtocolDecision` object containing status, explanation, and skipped step IDs.
- **Next Stage:** Canonical Event Generation.

### Stage 13: Confidence & Debouncing Handling
- **Input:** Sequence decisions.
- **Processing:** Temporal debouncing requires an action to be detected consistently across consecutive temporal inference strides before advancing the state machine. Prevents single-frame spurious spikes from falsely progressing the protocol.
- **Model:** Debounce streak tracker in `ProtocolDecisionEngine`.
- **Output:** Validated state machine transition.
- **Next Stage:** Event Bus.

### Stage 14: Canonical Event Generation & Output Dispatch
- **Input:** Validated decisions and perception snapshots.
- **Processing:** Publishes canonical events onto `EventBus`:
  - `StepCompleted`: Emitted when step invariants are verified.
  - `StepViolation`: Emitted on out-of-order or wrong-object actions.
  - `VoiceRequested`: Emitted to trigger TTS speech synthesis.
  - `ObservationCaptured`: Emitted for telemetry and GUI updates.
- **Output:** Dispatched events routed to audio synthesizer, SQLite persistence, and Qt GUI dashboard.
