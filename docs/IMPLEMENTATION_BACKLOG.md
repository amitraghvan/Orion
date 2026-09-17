# ORION SIH26174 IMPLEMENTATION BACKLOG
**Target Milestone:** Production-Grade SIH Compliance for On-board BAS Experiments  
**Engineering Discipline:** Zero-Assumption, Evidence-Based, Test-Driven Edge AI  
**Priorities:**
- **P0 (Critical / Blocker):** Missing or broken capabilities that prevent core SIH problem statement compliance.
- **P1 (Important):** Enhancements required for a complete, robust, and reliable operational system.
- **P2 (Robustness / Performance):** Edge acceleration, resource optimization, and latency tuning.
- **P3 (Advanced / Optional):** Long-term research extensions (e.g., orientation-agnostic 3D Human Mesh Recovery).

---

## P0 — CRITICAL BLOCKERS (Core SIH Compliance)

### `BLG-P0-01`: Fix HAR Runtime Feature Channel Mismatch
- **Priority:** P0 (Blocker)
- **Problem:** The ST-GCN model was trained on $[x_n, y_n, conf, interaction]$ where all 4 channels are normalized in $[0, 1]$. At runtime, [`app/intelligence/temporal_engine.py:79-90`](file:///Users/amitkumar/Orion/app/intelligence/temporal_engine.py#L79-L90) constructs an input tensor containing $[x_{px}, y_{px}, v_x, v_y]$ (raw pixel coordinates up to $640 \times 480$ and pixel velocity deltas). This makes live model inferences out-of-distribution and completely invalid.
- **Current State:** Broken. Runtime ST-GCN predictions on live camera or video frames are essentially random.
- **Solution:** Align `TemporalHAREngine` feature extraction with training expectations:
  1. Normalize $x$ and $y$ keypoint coordinates by frame width and height ($x / W$, $y / H$).
  2. Channel 2 must carry keypoint detection confidence ($c \in [0, 1]$).
  3. Channel 3 must carry hand-to-apparatus interaction proximity score ($prox \in [0, 1]$) computed from active detections or chromatic box masks.
- **Files to Modify:**
  - [`app/intelligence/temporal_engine.py`](file:///Users/amitkumar/Orion/app/intelligence/temporal_engine.py)
  - [`app/intelligence/intelligence_engine.py`](file:///Users/amitkumar/Orion/app/intelligence/intelligence_engine.py)
- **Dependencies:** NumPy, PyTorch.
- **Model / Data Requirement:** Uses active model weights [`models/bas_experiment/best.pt`](file:///Users/amitkumar/Orion/models/bas_experiment/best.pt).
- **Implementation Steps:**
  1. Update `push_frame_keypoints()` to accept frame dimensions $(W, H)$ and normalise coordinates.
  2. Accept keypoint confidence array and interaction proximity score.
  3. Re-assemble tensor as shape `(1, 4, 32, 17)` matching $[x_n, y_n, conf, prox]$.
- **Verification Test:** Unit test feeding synthetic normalized input matching `BAS_REAL_DATA` format and asserting valid output distribution.
- **Acceptance Criteria:** `predict_activity()` produces coherent probabilities matching offline evaluation and does not saturate on unnormalized coordinate magnitudes.

---

### `BLG-P0-02`: Wire Mission Recording & Local Video Storage
- **Priority:** P0 (Blocker)
- **Problem:** [`app/recording/recorder.py`](file:///Users/amitkumar/Orion/app/recording/recorder.py) implements video recording, but `start_recording()` is never invoked when an experiment is started. When an operator clicks "START MISSION" in [`app/ui/dashboard.py:254`](file:///Users/amitkumar/Orion/app/ui/dashboard.py#L254), no video writer is opened.
- **Current State:** Broken. No local experiment videos are ever saved to disk during application runs.
- **Solution:**
  1. Wire `start_recording()` directly into `experiment_engine.start_experiment()`.
  2. Ensure the recording writer ingests frames directly from the dedicated camera capture thread at full capture FPS (30 FPS), rather than the downstream inference loop (11 - 21 FPS), preventing video time compression.
  3. Wire `stop_recording()` into `experiment_engine.stop_experiment()` and the completion handler.
- **Files to Modify:**
  - [`app/experiments/experiment_engine.py`](file:///Users/amitkumar/Orion/app/experiments/experiment_engine.py)
  - [`app/recording/recorder.py`](file:///Users/amitkumar/Orion/app/recording/recorder.py)
  - [`app/application.py`](file:///Users/amitkumar/Orion/app/application.py)
- **Dependencies:** OpenCV (`cv2.VideoWriter`), PySide6.
- **Model / Data Requirement:** None.
- **Implementation Steps:**
  1. In `experiment_engine.start_experiment()`, call `experiment_recorder.start_recording(exp_id, run_id, width, height, fps)`.
  2. In `experiment_engine.stop_experiment()` and when the FSM reaches `COMPLETED`, call `experiment_recorder.stop_recording()`.
  3. In `camera_manager`, push raw captured frames directly to `experiment_recorder.push_frame(frame)`.
- **Verification Test:** Integration test executing a 10-second protocol run, verifying that `assets/recordings/<exp_id>_<run_id>/experiment.mp4` is created, playable, and has matching duration and frame rate.
- **Acceptance Criteria:** A valid MP4 file is created for every mission session with non-zero byte size and exact 30 FPS playback synchronization.

---

### `BLG-P0-03`: Wire Structured Output & Post-Mission Scientific Dossiers
- **Priority:** P0 (Blocker)
- **Problem:** [`app/reports/report_generator.py`](file:///Users/amitkumar/Orion/app/reports/report_generator.py) contains logic to generate Markdown and JSON mission dossiers, but it is never called by the application runtime. Session metadata and timeline event logs are never written to disk during real operations.
- **Current State:** Broken. Structured logs and compliance reports exist only in unit test mocks.
- **Solution:**
  1. In `experiment_engine.py`, when an experiment terminates (`COMPLETED` or `ABORTED`), collect session timeline events, calculate execution metrics, and invoke `report_generator.generate_report()`.
  2. Invoke `storage_manager.write_metadata()`, `write_events()`, and `write_timeline_log()` into the session directory.
- **Files to Modify:**
  - [`app/experiments/experiment_engine.py`](file:///Users/amitkumar/Orion/app/experiments/experiment_engine.py)
  - [`app/ui/dashboard.py`](file:///Users/amitkumar/Orion/app/ui/dashboard.py)
- **Dependencies:** Standard library (`json`, `pathlib`, `datetime`).
- **Model / Data Requirement:** Protocol execution timeline events.
- **Implementation Steps:**
  1. Create a completion hook in `ExperimentEngine` executed upon terminal states.
  2. Assemble `steps_log`, durations, compliance summary, and call `report_generator.generate_report(...)`.
  3. Expose generated report path on the UI and emit a desktop alert banner with link to open dossier.
- **Verification Test:** Automated end-to-end test simulating a full 4-step protocol, asserting `REPORT_<exp_id>_<run_id>.md` and `.json` exist in `reports/` with complete chronological tables.
- **Acceptance Criteria:** An immutable Markdown report and machine-readable JSON dossier are generated automatically upon every mission completion.

---

### `BLG-P0-04`: True IP Video Streaming to Specified Destination IP
- **Priority:** P0 (Blocker)
- **Problem:** [`app/streaming/stream_manager.py`](file:///Users/amitkumar/Orion/app/streaming/stream_manager.py) implements a pull-based HTTP MJPEG server bound to `127.0.0.1:8080`, disabled by default. It cannot stream video to a specific remote destination IP (e.g., ground station or observation terminal `192.168.1.150:5000`).
- **Current State:** Misaligned. Only supports pull HTTP requests from the local machine.
- **Solution:**
  1. Implement configurable push-based network video transmission:
     - **Mode 1 (Unicast UDP/RTP):** Transmit packetized H.264/JPEG frames directly to `destination_ip:destination_port` via UDP socket or GStreamer/FFmpeg pipe.
     - **Mode 2 (Network-Accessible HTTP/RTSP):** When bound to `0.0.0.0`, allow remote observation clients to view the live video feed from external IP addresses.
  2. Add `destination_ip` and `destination_port` fields to `StreamingConfig`.
- **Files to Modify:**
  - [`app/core/config.py`](file:///Users/amitkumar/Orion/app/core/config.py)
  - [`app/streaming/stream_manager.py`](file:///Users/amitkumar/Orion/app/streaming/stream_manager.py)
  - [`app/ui/settings_view.py`](file:///Users/amitkumar/Orion/app/ui/settings_view.py)
- **Dependencies:** Python `socket`, OpenCV.
- **Model / Data Requirement:** Live camera BGR frames.
- **Implementation Steps:**
  1. Extend `StreamingConfig` with `mode: "unicast_udp" | "mjpeg_http"`, `destination_ip: str = "127.0.0.1"`, `destination_port: int = 5000`.
  2. Implement `UDPStreamClient` that serializes compressed JPEG frames into UDP datagrams pushed to `(destination_ip, destination_port)`.
  3. Ensure `MJPEGHandler` binds to `0.0.0.0` when network broadcast is enabled.
- **Verification Test:** Test streaming across local virtual interfaces: transmit from `127.0.0.1` to UDP port `9999`, verify client receives valid image headers.
- **Acceptance Criteria:** Video frames are actively transmitted to a configured destination IP without requiring manual browser pull from localhost.

---

### `BLG-P0-05`: Synthetic Kinetic Augmentation & Generalization for ST-GCN
- **Priority:** P0 (Blocker)
- **Problem:** On held-out test subject `SP04`, the fine-tuned ST-GCN achieves only **2.98% accuracy** (Macro F1 = 0.0146) due to small sample size (20 videos) and uniform time-slice pseudo-labels.
- **Current State:** Broken / Failed generalization.
- **Solution:**
  1. Create kinetic data augmentation module for skeleton sequences:
     - 3D spatial rotation perturbation ($\pm 15^\circ$)
     - Temporal elastic stretching and compression ($\pm 20\%$)
     - Gaussian coordinate jitter ($\sigma = 0.01$)
     - Random joint dropout ($p = 0.05$)
  2. Implement re-labeling of training sequences using true kinematic velocity peaks (onset of hand motion to box contact) rather than linear uniform duration slicing.
  3. Re-train ST-GCN with balanced class sampling and cross-entropy + label smoothing ($0.1$).
- **Files to Create / Modify:**
  - `ai/src/orion_ai/activity/augmentation.py` [NEW]
  - [`scripts/prepare_bas_dataset.py`](file:///Users/amitkumar/Orion/scripts/prepare_bas_dataset.py)
  - [`scripts/train_bas_har.py`](file:///Users/amitkumar/Orion/scripts/train_bas_har.py)
- **Dependencies:** PyTorch, TorchVision.
- **Model / Data Requirement:** `datasets/bas_experiment/sequences/`
- **Implementation Steps:**
  1. Build `KineticAugmentation` pipeline in `ai/src/orion_ai/activity/augmentation.py`.
  2. Inject augmentation into PyTorch `Dataset.__getitem__` during training mode.
  3. Re-train `models/bas_experiment/best.pt` for 40 epochs with cosine annealing schedule.
- **Verification Test:** Evaluate re-trained model on `datasets/bas_experiment/sequences/test/` using [`scripts/evaluate_bas_har.py`](file:///Users/amitkumar/Orion/scripts/evaluate_bas_har.py).
- **Acceptance Criteria:** Held-out subject test accuracy reaches $\ge 75\%$ (Macro F1 $\ge 0.70$) with non-zero precision across all 8 classes.

---

## P1 — IMPORTANT SYSTEM CAPABILITIES (Completeness & Reliability)

### `BLG-P1-01`: Domain-Specific Glovebox Object Detection
- **Priority:** P1 (Important)
- **Problem:** YOLO11n currently detects COCO classes (`person`, `bus`, `bottle`), while BAS experiments require detecting `yellow_box`, `red_box`, `glovebox_container`, `inspection_zone`.
- **Current State:** Misaligned. The app pairs hands with generic COCO objects or fails detection.
- **Solution:**
  1. Integrate the chromatic-spatial box filter from [`scripts/test_improved_box_detection.py`](file:///Users/amitkumar/Orion/scripts/test_improved_box_detection.py) directly into the primary perception pipeline as an immediate, deterministic zero-shot detector for yellow/red flight boxes.
  2. Annotate 500 frames from the raw experiment videos for fine-tuning YOLO11n to `models/weights/yolo11n_bas.pt` with domain classes.
- **Files to Modify:**
  - [`app/intelligence/intelligence_engine.py`](file:///Users/amitkumar/Orion/app/intelligence/intelligence_engine.py)
  - [`app/intelligence/hand_object_engine.py`](file:///Users/amitkumar/Orion/app/intelligence/hand_object_engine.py)
- **Dependencies:** OpenCV, NumPy.
- **Model / Data Requirement:** `yolo11n_bas.pt` or chromatic spatial filter.
- **Implementation Steps:**
  1. Embed `ChromaticBoxDetector` into `IntelligenceEngine.process_frame()`.
  2. Inject detected apparatus boxes (`yellow_box`, `red_box`) into `detected_objects` list alongside YOLO detections.
  3. Ensure tracker maintains consistent identities across frames.
- **Verification Test:** Test frame containing yellow and red boxes; verify tracker outputs IDs with class names `yellow_box` and `red_box`.
- **Acceptance Criteria:** Yellow and red experiment containers are detected with precision $\ge 90\%$ under varying glovebox illumination.

---

### `BLG-P1-02`: Temporal Contact & Manipulation HOI Verification
- **Priority:** P1 (Important)
- **Problem:** Current HOI evaluation is a static 2D distance threshold from wrist keypoints. It cannot distinguish an astronaut resting their hand near a box from an actual grasp and transport action.
- **Current State:** Heuristic prototype.
- **Solution:**
  1. Upgrade `HandObjectInteractionEngine` to track dynamic object displacement:
     - When hand is in `TOUCH` state ($dist < 70$ px) AND object bounding box velocity matches hand velocity vector ($\Delta \vec{x}_{obj} \approx \Delta \vec{x}_{hand} \neq 0$), classify as `MANIPULATE`.
     - When hand moves away and object ceases movement, classify as `RELEASE`.
- **Files to Modify:**
  - [`app/intelligence/hand_object_engine.py`](file:///Users/amitkumar/Orion/app/intelligence/hand_object_engine.py)
- **Dependencies:** NumPy, Math.
- **Model / Data Requirement:** Tracked object history, pose keypoints.
- **Implementation Steps:**
  1. Maintain 10-frame displacement history for both hand center and object center.
  2. Compute cross-correlation of velocity vectors.
  3. Output validated `MANIPULATE` state only when mutual displacement exceeds 15 pixels.
- **Verification Test:** Unit test with synthetic stationary vs moving object trajectories, verifying no false `MANIPULATE` triggers while stationary.
- **Acceptance Criteria:** Interaction state machine transitions reliably through `APPROACH -> TOUCH -> MANIPULATE -> RELEASE`.

---

### `BLG-P1-03`: Step Timeout & Strict Violation Guidance
- **Priority:** P1 (Important)
- **Problem:** Step timeouts are specified in protocol YAMLs (`timeout_seconds: 30.0`), but `ProtocolDecisionEngine` never checks wall-clock duration against this threshold. Additionally, guidance on violations does not provide corrective instructions.
- **Current State:** Partial. FSM transitions ignore timeout; operator guidance does not instruct how to recover from an error.
- **Solution:**
  1. In `decision_engine.evaluate()`, check `(now - step_start_time) > step.timeout_seconds`. If exceeded, return `DecisionStatus.TIMEOUT`.
  2. In `next_step_engine.py`, add corrective guidance generation for `WRONG_OBJECT` and `OUT_OF_SEQUENCE`.
- **Files to Modify:**
  - [`app/intelligence/decision_engine.py`](file:///Users/amitkumar/Orion/app/intelligence/decision_engine.py)
  - [`app/intelligence/next_step_engine.py`](file:///Users/amitkumar/Orion/app/intelligence/next_step_engine.py)
- **Dependencies:** Standard library `datetime`.
- **Implementation Steps:**
  1. Add timeout branch returning `DecisionStatus.TIMEOUT`.
  2. Upon timeout or violation, update guidance card with action: *"Return red box to rack and pick yellow box to resume Step 1"*.
- **Verification Test:** Set timeout to 2 seconds, wait 3 seconds, verify FSM flags `TIMEOUT` and issues voice notification.
- **Acceptance Criteria:** Steps exceeding allocated flight timeline trigger explicit timeout events and acoustic annunciations.

---

## P2 — ROBUSTNESS & EDGE ACCELERATION

### `BLG-P2-01`: Pure Air-Gap Hardening & Ultralytics Telemetry Elimination
- **Priority:** P2 (Robustness)
- **Problem:** Ultralytics YOLO has built-in telemetry / sync analytics that triggers network socket checks if unconfigured. `scripts/generate_sample_video.py` has an unhandled HTTP request to GitHub.
- **Current State:** Partial air-gap.
- **Solution:**
  1. Set `YOLO_OFFLINE=1` and `ULTRALYTICS_CONFIG_DIR` environment variables during application startup.
  2. Disable Ultralytics analytics programmatically: `from ultralytics import settings; settings.update({"sync": False})`.
  3. Remove external HTTP download fallback in `generate_sample_video.py` and replace with pure synthetic generation.
- **Files to Modify:**
  - [`app/main.py`](file:///Users/amitkumar/Orion/app/main.py)
  - [`app/models/pytorch_backend.py`](file:///Users/amitkumar/Orion/app/models/pytorch_backend.py)
  - [`scripts/generate_sample_video.py`](file:///Users/amitkumar/Orion/scripts/generate_sample_video.py)
- **Dependencies:** Ultralytics, OS.
- **Verification Test:** Run entire application under `unshare -n` (Linux) or with network adapter disabled, verifying zero network exceptions.
- **Acceptance Criteria:** Application boots, processes video, performs inference, speaks alerts, and records without network connectivity.

---

### `BLG-P2-02`: Frame Decoupling for Full 30 FPS Recording and Display
- **Priority:** P2 (Performance)
- **Problem:** Currently, display emission and video recording pushes occur inside `_inference_worker` in [`app/application.py:183`](file:///Users/amitkumar/Orion/app/application.py#L183). This throttles the GUI display and local video recording to the inference FPS (11 - 21 FPS).
- **Current State:** Display and recording bound to perception latency.
- **Solution:**
  1. Move `recorder.push_frame()` and GUI `dispatcher.frame_ready.emit()` into `CameraManager` capture thread or a dedicated 30 FPS display thread.
  2. Overlay latest available inference snapshot asynchronously onto the high-speed video stream.
- **Files to Modify:**
  - [`app/application.py`](file:///Users/amitkumar/Orion/app/application.py)
  - [`app/camera/camera_sources.py`](file:///Users/amitkumar/Orion/app/camera/camera_sources.py)
- **Acceptance Criteria:** GUI video view and recorded MP4 maintain full 30 FPS smooth rendering regardless of perception model latency.

---

## P3 — ADVANCED RESEARCH EXTENSIONS (Optional)

### `BLG-P3-01`: Orientation-Agnostic 3D Human Mesh Recovery (FastHMR)
- **Priority:** P3 (Optional SIH Requirement)
- **Problem:** Astronauts in zero-gravity operate in non-canonical orientations (upside down, sideways). 2D skeleton normalization handles translation and scale, but true 3D joint rotations require mesh regression.
- **Current State:** Missing. Documented in research papers only.
- **Solution:**
  1. Implement a lightweight 2D-to-3D skeletal lifting network (MLP or lightweight GCN) predicting 3D joint rotations $(X, Y, Z)$ from 2D COCO keypoints in $<1$ ms.
  2. Render 3D wireframe skeleton in PySide6 `LiveView`.
- **Files to Create:**
  - `ai/src/orion_ai/pose/fast_hmr.py` [NEW]
  - `app/ui/widgets/pose_3d_widget.py` [NEW]
- **Dependencies:** PyTorch, OpenGL / QtDataVisualization.
- **Acceptance Criteria:** 3D skeletal posture is rendered in real-time with zero internet dependencies.
