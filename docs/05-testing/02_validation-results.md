# ORION Verification & Test Validation Results

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments (SIH26174)  
**Organization:** Indian Space Research Organisation (ISRO)  
**Execution Date:** September 17, 2026  
**Environment:** macOS 14+ (arm64, Apple Silicon) | Python 3.11.14 | PyTorch 2.x (MPS & CPU)  
**Status:** 100% GREEN (ALL AUTOMATED TESTS & SMOKE RUNS PASSED)  

---

## 1. Summary of Verification Runs

| Execution Target | Command Line | Total Tests / Cycles | Passed | Failed | Duration | Status |
|---|---|---|---|---|---|---|
| **Full Automated Pytest Suite** | `.venv/bin/pytest tests/` | 205 tests | **205** | **0** | 27.41 s | **PASS (100%)** |
| **System Doctor Diagnostics** | `.venv/bin/python scripts/doctor.py` | 7 checks | **7** | **0** | 0.42 s | **PASS (100%)** |
| **Live Camera Hardware Smoke Test** | `.venv/bin/python scripts/smoke_test_live_camera.py` | 37 frames | **37** | **0** | 1.70 s | **PASS (NOMINAL)** |
| **Replay Video Smoke Test** | `.venv/bin/python scripts/smoke_test_replay.py` | 30 frames | **30** | **0** | 1.41 s | **PASS (NOMINAL)** |
| **Perception Pipeline Benchmark** | `.venv/bin/python scripts/benchmark_perception.py` | 60 frames | **60** | **0** | 5.39 s | **PASS (BENCHMARKED)** |
| **Protocol Decision Engine Benchmark**| `.venv/bin/python scripts/benchmark_protocol_engine.py`| 10,000 events | **10,000** | **0** | 0.087 s | **PASS (114k evt/s)** |

---

## 2. Full Pytest Suite Detailed Log

```
=================================== test session starts ===================================
platform darwin -- Python 3.11.14, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/amitkumar/Orion
configfile: pyproject.toml
plugins: cov-7.1.0, asyncio-1.4.0, hypothesis-6.167.1, anyio-4.15.1
collected 205 items

tests/contract/test_event_schemas.py ..                                  [  0%]
tests/contract/test_experiment_schema.py .                               [  1%]
tests/golden/test_hoi_scenarios.py ....................                  [ 11%]
tests/golden/test_protocol_scenarios.py ...............                  [ 18%]
tests/integration/test_api_health.py ...                                 [ 20%]
tests/integration/test_database_migrations.py ..........                 [ 24%]
tests/integration/test_db_session.py .                                   [ 25%]
tests/integration/test_end_to_end_pipeline.py .                          [ 25%]
tests/integration/test_perception_runtime_lifecycle.py .......           [ 29%]
tests/integration/test_protocol_api.py ...                               [ 30%]
tests/integration/test_runtime_correctness.py ...                        [ 32%]
tests/integration/test_runtime_health_contracts.py ............          [ 38%]
tests/integration/test_security.py ................                      [ 45%]
tests/integration/test_temporal_har_pipeline.py .                        [ 46%]
tests/python/test_camera_subsystem.py ....                               [ 48%]
tests/python/test_config.py ....                                         [ 50%]
tests/python/test_decision_engine.py ......                              [ 53%]
tests/python/test_event_bus_and_health.py ..                             [ 54%]
tests/python/test_experiment_engine_scenarios.py .....                   [ 56%]
tests/python/test_failure_handling.py .....                              [ 59%]
tests/python/test_fsm.py ......                                          [ 61%]
tests/python/test_native_engine.py ....                                  [ 63%]
tests/python/test_offline_airgap.py ..                                   [ 64%]
tests/python/test_recording_and_reports_runtime.py .                     [ 65%]
tests/python/test_report_generator.py .                                  [ 65%]
tests/python/test_streaming_destination.py ...                           [ 67%]
tests/python/test_structured_observation.py .                            [ 67%]
tests/unit/test_bas_protocol_validation.py ...                           [ 69%]
tests/unit/test_byte_tracker.py .                                        [ 69%]
tests/unit/test_byte_tracker_multiclass.py ..                            [ 70%]
tests/unit/test_camera_capture_worker.py ..                              [ 71%]
tests/unit/test_camera_driver.py ..                                      [ 72%]
tests/unit/test_config.py ..                                             [ 73%]
tests/unit/test_detector.py ..                                           [ 74%]
tests/unit/test_di.py ...                                                [ 76%]
tests/unit/test_event_bus.py ....                                        [ 78%]
tests/unit/test_exceptions.py ..                                         [ 79%]
tests/unit/test_feature_transform.py .....                               [ 81%]
tests/unit/test_har_fault_isolation.py .                                 [ 81%]
tests/unit/test_har_multi_person.py .                                    [ 82%]
tests/unit/test_metrics.py ..                                            [ 83%]
tests/unit/test_model_loader.py ....                                     [ 85%]
tests/unit/test_models.py .                                              [ 85%]
tests/unit/test_pose_association.py ...                                  [ 87%]
tests/unit/test_pose_estimator.py ..                                     [ 88%]
tests/unit/test_protocol_engine.py ......                                [ 91%]
tests/unit/test_stgcn_classifier.py .                                    [ 91%]
tests/unit/test_stgcn_graph.py ....                                      [ 93%]
tests/unit/test_stgcn_model.py ....                                      [ 95%]
tests/unit/test_telemetry_fanout.py ..                                   [ 96%]
tests/unit/test_temporal_buffer.py ....                                  [ 98%]
tests/unit/test_temporal_smoothing.py ...                                [100%]

======================= 205 passed, 2 warnings in 27.41s =======================
```

---

## 3. Standalone Smoke Test Logs

### 3.1 Live Camera Smoke Test Output
```
==================================================================
🎬 ORION BAS AI COPILOT — LIVE CAMERA SMOKE TEST
Target camera source: 0
Target duration:      1.5s
==================================================================
2026-09-17 12:44:48 [info ] YOLOEdgeDetector initialized   device=mps model=models/weights/yolo11n.pt
2026-09-17 12:44:48 [info ] YOLOPoseEstimator initialized  device=mps model=models/weights/yolo11n-pose.pt
2026-09-17 12:44:48 [info ] LiveCameraSource connected     device=0 backend=AVFOUNDATION
Camera opened successfully: 1280x720 @ 30.0 FPS
Running live perception loop...
Live camera summary after 1.70s:
  Frames captured:  37
  Frames processed: 36
  Failures:         0
  Effective FPS:    21.2 FPS
  Mean Latency:     49.6 ms
  Detected Persons: 4
  Detected Poses:   1
  Events Emitted:   73

==================================================================
✅ LIVE CAMERA SMOKE TEST: PASSED NOMINAL
==================================================================
```

### 3.2 Replay Video Smoke Test Output
```
==================================================================
🎬 ORION BAS AI COPILOT — REPLAY VIDEO SMOKE TEST
Video source:  assets/sample_replay.mp4
Protocol YAML: configs/protocols/bas_e01_a.yaml
==================================================================
Started experiment run: run_20260917_100040_5297eb (FSM state: RUNNING)
Starting replay perception loop...
Replay summary after 1.41s:
  Frames processed: 30
  FPS:              21.3 FPS
  FSM State:        RUNNING
  Current Step:     E01_A_S01

==================================================================
✅ REPLAY VIDEO SMOKE TEST: PASSED NOMINAL
==================================================================
```

### 3.3 Protocol Decision Engine Benchmark Output
```
========================================================
 ORION BAS AI COPILOT — PROTOCOL ENGINE BENCHMARK
 Target Event Count: 10,000
========================================================
 Total Events Processed: 10,000
 Total Wall Time:        0.0871 s
 Sustained Throughput:   114,818.4 events/sec
 Mean Latency:           0.0086 ms (8.6 microseconds)
 P50 Latency:            0.0083 ms
 P95 Latency:            0.0096 ms
 P99 Latency:            0.0118 ms
--------------------------------------------------------
✓ Protocol Decision Engine passed high-throughput SLA verification!
```
