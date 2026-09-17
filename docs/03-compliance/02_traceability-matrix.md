# ORION SIH26174 Traceability Matrix

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments (SIH26174)  
**Organization:** Indian Space Research Organisation (ISRO)  
**Date:** September 17, 2026  
**Status:** FULL TRACEABILITY ESTABLISHED  

---

## 1. End-to-End Requirement-to-Implementation Traceability

Every official requirement is mapped directly to its concrete implementation files, classes, functions, and automated test cases:

| Req ID | Requirement | Subsystem | Concrete File | Implementing Class / Function | Verification Test | Evidence & Artifact |
|---|---|---|---|---|---|---|
| **R01** | Continuous local video processing | Camera | `ai/src/orion_ai/camera/camera_sources.py` | `LiveCameraSource.read_frame()` | `tests/python/test_camera_subsystem.py::test_camera_manager_lifecycle` | 37 frames captured, 0 dropped, 21.2 FPS in live smoke test |
| **R02** | Experiment sequence tracking | Protocol | `backend/src/orion/protocol/state_machine.py` | `ProtocolStateMachine.advance_step()` | `tests/python/test_fsm.py::test_full_execution_lifecycle` | FSM transitions verified across all states |
| **R03** | Next-step guidance | Protocol | `backend/src/orion/protocol/next_step_engine.py` | `NextStepEngine.compute_guidance()` | `tests/unit/test_protocol_engine.py::test_next_step_guidance_engine` | Guidance instruction text emitted at step transition |
| **R04** | Skipped step detection | Intelligence | `app/intelligence/decision_engine.py` | `ProtocolDecisionEngine.evaluate()` | `tests/python/test_decision_engine.py::test_out_of_sequence_and_skipped` | Flags skipped step IDs and emits warning |
| **R05** | Out-of-sequence detection | Intelligence | `app/intelligence/decision_engine.py` | `ProtocolDecisionEngine.evaluate()` | `tests/python/test_decision_engine.py::test_out_of_sequence_and_skipped` | Returns `DecisionStatus.OUT_OF_SEQUENCE` |
| **R06** | Voice alerts | Audio | `app/audio/tts_engine.py` | `TTSEngine.speak()` | `tests/python/test_failure_handling.py::test_tts_engine_graceful_fallback_when_unavailable` | Offline speech synthesis with cooldown |
| **R07** | Structured timestamped logs | Storage | `app/recording/storage_manager.py` | `StorageManager.write_events()` | `tests/python/test_report_generator.py::test_generate_report` | `metadata.json`, `events.json`, SQLite DB |
| **R08** | Outcomes and status | Intelligence | `app/intelligence/decision_engine.py` | `ProtocolDecision.status` | `tests/python/test_decision_engine.py` | Status enum serialized in logs and telemetry |
| **R09** | IP video streaming | Streaming | `app/streaming/stream_manager.py` | `StreamManager.start()` | Manual verified / `tests/unit/` | HTTP MJPEG stream at `http://127.0.0.1:8080/live` |
| **R10** | Local video storage | Recording | `app/recording/recorder.py` | `ExperimentRecorder.push_frame()` | `tests/unit/test_camera_driver.py` | Asynchronous MP4 writer in `recordings/` |
| **R11** | Graphical monitoring UI | Desktop GUI | `app/ui/main_window.py` | `MainWindow.__init__()` | `tests/python/test_native_engine.py` | PySide6 QMainWindow with 10 tabbed cockpit views |
| **R12** | Offline standalone AI | AI / HAR | `ai/src/orion_ai/activity/stgcn_classifier.py` | `STGCNClassifier.predict()` | `tests/unit/test_stgcn_classifier.py` | Weights in `models/bas_experiment/best.pt`, 0 network calls |
| **R13** | Custom focused dataset | Datasets | `datasets/bas_experiment/` | Raw recordings & annotations | `scripts/audit_bas_dataset.py` | 20 video recordings audited in `raw_data_audit.json` |
| **R14** | Multi-task CV (Det, Pose, HOI)| Perception | `app/intelligence/hand_object_engine.py` | `HandObjectInteractionEngine.evaluate_interactions()` | `tests/integration/test_end_to_end_pipeline.py` | Hands, joints, and contact states extracted |
| **R15** | 3D Human Mesh Recovery (Opt) | AI / Research| `docs/research/research-paper.md` | Normalization in `graph.py` | `tests/unit/test_stgcn_graph.py::test_microgravity_translation_invariance` | Microgravity invariance verified; 3D mesh modeled |
