# CLAIM-EVIDENCE TRACEABILITY MATRIX: ORION
**Document ID:** ORION-CEM-2026-010  
**Classification:** Research Verification & Claim Audit Matrix  
**Date:** September 2026  
**Repository Path:** `/Users/amitkumar/Orion`  
**SIH Problem Statement:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments  

---

## 1. Overview & Evaluation Standards

This matrix provides strict, bidirectional traceability between every scientific and technical assertion made in the research paper and the underlying source code, configuration files, checkpoint manifests, and benchmark logs in the repository.

### Status Taxonomy:
- **`VERIFIED`**: Directly executed and confirmed by empirical data or passing automated tests in the repository.
- **`PARTIALLY VERIFIED`**: Implemented in code, but empirical evaluation is restricted to a small sample size or proxy environment.
- **`IMPLEMENTED BUT NOT EVALUATED`**: Fully operational source code present, but formal quantitative benchmarks are pending.
- **`STUB / PLANNED`**: Defined as an architectural interface or future work; no operational implementation exists.
- **`UNSUPPORTED`**: Any claim not supported by repository evidence; strictly excluded from the paper.

---

## 2. Complete Traceability Matrix

| Claim ID | Paper Claim Description | Repository File | Specific Code Location | Empirical Evidence File | Verification Status |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **C-01** | Optical ingestion uses a dedicated capture thread and ring buffer (`maxlen=2`) to decouple I/O. | `ai/src/orion_ai/camera/opencv_driver.py` | Lines 26–180 (`_CaptureWorkerThread`) | `tests/unit/test_camera_capture_worker.py` | **VERIFIED** |
| **C-02** | YOLO11n is used for 2D bounding box object detection with 2.6M parameters. | `ai/src/orion_ai/detection/yolo_detector.py` | Lines 1–120 (`YOLOEdgeDetector`) | `models/weights/yolo11n.manifest.json` | **VERIFIED** |
| **C-03** | YOLO11n-pose estimates 17 COCO skeletal keypoints with 2.9M parameters. | `ai/src/orion_ai/pose/yolo_pose.py` | Lines 1–140 (`YOLOPoseEstimator`) | `models/weights/yolo11n-pose.manifest.json` | **VERIFIED** |
| **C-04** | ByteTrack maintains multi-object identity persistence with Kalman filtering. | `ai/src/orion_ai/tracking/byte_tracker.py` | Lines 1–250 (`ByteTracker`) | `tests/unit/test_byte_tracker.py` | **VERIFIED** |
| **C-05** | Hand regions are derived kinematically from COCO wrist keypoints 9 & 10 with 0 extra forward passes. | `ai/src/orion_ai/hand/extractor.py` | Lines 21–120 (`PoseBasedHandExtractor`) | `docs/architecture/adr_011_hand_perception.md` | **VERIFIED** |
| **C-06** | Hand-Object association uses Hungarian bipartite matching on distance and IoU overlap. | `ai/src/orion_ai/interaction/hand_object_associator.py` | Lines 32–110 (`HandObjectAssociator`) | `tests/unit/test_pose_association.py` | **VERIFIED** |
| **C-07** | HOI state transitions enforce temporal hysteresis across 5 discrete interaction states. | `ai/src/orion_ai/interaction/state_machine.py` | Lines 32–180 (`InteractionStateMachine`) | `docs/architecture/adr_013_hand_object_interaction.md` | **VERIFIED** |
| **C-08** | ST-GCN operates on an input tensor shape of $(B, 4, 32, 17)$ with 455,194 parameters. | `ai/src/orion_ai/activity/stgcn/model.py` | Lines 126–185 (`STGCNHARModel`) | `models/weights/stgcn_har_v1.manifest.json` | **VERIFIED** |
| **C-09** | Skeleton graph uses 3 spatial partitions (root, inward, outward) over 17 joints. | `ai/src/orion_ai/activity/stgcn/graph.py` | Lines 1–95 (`SkeletonGraph`) | `tests/unit/test_stgcn_graph.py` | **VERIFIED** |
| **C-10** | ST-GCN inference runs at an 8-frame stride (~3.75 Hz), saving 73% compute. | `ai/src/orion_ai/activity/runtime.py` | Lines 28–180 (`TemporalHARRuntime`) | `tests/integration/test_temporal_har_pipeline.py` | **VERIFIED** |
| **C-11** | Predictions are smoothed across a rolling 5-window buffer. | `ai/src/orion_ai/activity/smoothing.py` | Lines 15–80 (`TemporalPredictionSmoother`) | `tests/unit/test_temporal_smoothing.py` | **VERIFIED** |
| **C-12** | Shannon entropy filter flags predictions with $H(p) > 1.40$ as `STEP_UNCERTAIN`. | `ai/src/orion_ai/activity/smoothing.py` | Lines 82–140 (`UncertaintyEvaluator`) | `backend/src/orion/protocol/decision_engine.py` | **VERIFIED** |
| **C-13** | Multimodal fusion defines progressive verification Levels 0 to 3. | `ai/src/orion_ai/interaction/fusion.py` | Lines 23–175 (`DeterministicMultimodalFusion`) | `docs/architecture/adr_014_multimodal_evidence_fusion.md` | **VERIFIED** |
| **C-14** | Protocol state machine defines 11 discrete operational states. | `backend/src/orion/protocol/state_machine.py` | Lines 18–101 (`ProtocolStateMachine`) | `tests/unit/test_protocol_engine.py` | **VERIFIED** |
| **C-15** | Decision engine enforces safety invariant: $UNKNOWN \ne WRONG$ (`WAITING_FOR_EVIDENCE`). | `backend/src/orion/protocol/decision_engine.py` | Lines 222–237 | `tests/unit/test_protocol_engine.py` | **VERIFIED** |
| **C-16** | Decision engine enforces safety invariant: $UNCERTAIN \ne VIOLATION$ (`STEP_UNCERTAIN`). | `backend/src/orion/protocol/decision_engine.py` | Lines 198–221 | `tests/unit/test_protocol_engine.py` | **VERIFIED** |
| **C-17** | Decision engine enforces safety invariant: $NOT\_DETECTED \ne SKIPPED$. | `backend/src/orion/protocol/decision_engine.py` | Lines 340–380 | `tests/unit/test_protocol_engine.py` | **VERIFIED** |
| **C-18** | Protocol state transitions require a debouncing streak of $K=2$ consecutive windows. | `backend/src/orion/protocol/decision_engine.py` | Lines 76, 245–280 | `tests/unit/test_protocol_engine.py` | **VERIFIED** |
| **C-19** | Decision engine throughput reaches 132,778.6 events/sec (0.0074 ms/decision). | `scripts/benchmark_protocol_engine.py` | Lines 1–110 | `docs/phase_1_5_audit.md:116` | **VERIFIED** |
| **C-20** | `BAS_REAL_DATA` consists of 20 videos, 287.6s total duration, 11,550 frames, 4 subjects. | `datasets/bas_experiment/reports/raw_data_audit.json` | Complete JSON inventory | `datasets/bas_experiment/reports/raw_data_audit.md` | **VERIFIED** |
| **C-21** | Zero-leakage subject-level split partitions `SP01`/`SP02` (train), `SP03` (val), `SP04` (test). | `datasets/bas_experiment/metadata/splits.json` | Lines 1–29 | `reports/bas_training_report.md` | **VERIFIED** |
| **C-22** | Pure ST-GCN trained for 25 epochs on MPS achieves 96.41% train acc and 24.78% val acc. | `models/bas_experiment/metrics.json` | Lines 1–215 | `reports/bas_training_report.md` | **VERIFIED** |
| **C-23** | Pure ST-GCN top-1 accuracy on held-out subject `SP04` + anomalies drops to 2.98% (Macro F1 0.0146). | `models/bas_experiment/evaluation.json` | Lines 1–56 | `models/bas_experiment/confusion_matrix.png` | **VERIFIED** |
| **C-24** | Hybrid ORION engine achieves 100% detection rate on Wrong Object and Wrong Order anomalies. | `models/bas_experiment/evaluation.json` | Lines 57–66 | `reports/bas_training_report.md:98` | **VERIFIED** |
| **C-25** | Hybrid ORION engine achieves 0.0% false violation rate across 7 valid held-out test clips. | `models/bas_experiment/evaluation.json` | Lines 65 | `reports/bas_training_report.md:100` | **VERIFIED** |
| **C-26** | Interruption anomaly was detected at 0.0% in `RAW_video_20260912_183146.mp4`. | `models/bas_experiment/evaluation.json` | Line 64 | `scripts/evaluate_bas_har.py:166` | **VERIFIED** |
| **C-27** | End-to-end CPU pipeline latency is 71.12–78.31 ms (12.77–14.05 FPS). | `scripts/benchmark_perception.py` | Lines 1–146 | `docs/phase_1_3_audit.md:17` | **VERIFIED** |
| **C-28** | MPS acceleration reduces detection latency to 12.72 ms and pose to 14.10 ms. | `docs/phase_1_5_audit.md` | Lines 120–132 | `reports/bas_training_report.md:14` | **VERIFIED** |
| **C-29** | Asynchronous persistence decouples high-rate frames from database via queue (`maxsize=1000`). | `backend/src/orion/db/persistence_subscriber.py` | Lines 49–163 | `docs/architecture/adr_004_event_taxonomy_storage_decoupling.md` | **VERIFIED** |
| **C-30** | WebSocket broadcast omits raw base64 JPEG to ensure sub-5ms telemetry fanout. | `backend/src/orion/api/routers/telemetry_ws.py` | Lines 153–180 (`"image_jpeg": None`) | `docs/architecture/adr_003_inference_serialization_offload.md` | **VERIFIED** |
| **C-31** | Live video is streamed to browser via multipart MJPEG HTTP endpoint. | `backend/src/orion/api/routers/camera.py` | Lines 273–305 (`/camera/stream`) | `frontend/src/components/OpticalFeed.tsx:55` | **VERIFIED** |
| **C-32** | Voice guidance is executed client-side via Web Speech API with a 4,000 ms debounce timer. | `frontend/src/components/cockpit/VoiceAlertSystem.tsx` | Lines 12–44 (`window.speechSynthesis`) | Browser runtime testing | **VERIFIED** |
| **C-33** | Backend TTS daemon (`backend/src/orion/audio/interfaces.py`) is fully implemented. | `backend/src/orion/audio/interfaces.py` | Lines 37–96 (Raises `NotImplementedError`) | None | **REFUTED (STUB)** |
| **C-34** | Hardware video recording / FFmpeg muxing is fully operational on backend. | `backend/src/orion/recording/interfaces.py` | Lines 33–60 (Raises `NotImplementedError`) | None | **REFUTED (STUB)** |
| **C-35** | RTSP / WebRTC streaming server is fully operational on backend. | `backend/src/orion/streaming/interfaces.py` | Lines 25–60 (Raises `NotImplementedError`) | None | **REFUTED (STUB)** |
| **C-36** | ORION is currently flight-qualified and actively deployed on the Bharatiya Antariksh Station. | N/A | Ground prototype for SIH26174 | None | **REFUTED (FUTURE WORK)** |
