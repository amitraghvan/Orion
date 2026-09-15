# ORION — BAS AI Copilot (SIH26174)
# Phase 1.3 Residual & Deferred Change Ledger

| ID | Issue | Source | Severity | Current State | Phase 1.3 Required? | Action | Verification | Status |
|---|---|---|---|---|---|---|---|---|
| LED-01 | Absence of temporal feature buffer | SIH26174 SeqReq | **P0** | No buffer exists | **YES** | Implement `TemporalFeatureBuffer` with configurable $T$, $S$, stale timeout, and per-track isolation | `test_temporal_buffer.py` | **PLANNED** |
| LED-02 | Keypoint missing-data blind interpolation risk | User Req #7 | **P1** | N/A | **YES** | Tag keypoints with `OBSERVED`, `INTERPOLATED`, `HELD`, `INVALID` and decay confidence | `test_temporal_buffer.py` | **PLANNED** |
| LED-03 | Uncalibrated microgravity skeleton coordinates | SIH26174 MicroG | **P0** | Raw pixel bbox only | **YES** | Implement `MicrogravityNormalizer` (mid-hip root centering, trunk scale with $\epsilon$, velocities) | `test_stgcn_graph.py` | **PLANNED** |
| LED-04 | Overclaiming 3D orientation invariance | User Req #4 | **P1** | Documentation risk | **YES** | Frame as "Microgravity-motivated baseline" and add rotation perturbation test | `test_stgcn_graph.py` | **PLANNED** |
| LED-05 | Absence of real ST-GCN neural network | Phase 1.3 Goal | **P0** | Phase 0 stub | **YES** | Implement PyTorch `STGCNHARModel` with learnable spatial graph and temporal convolutions | `test_stgcn_model.py` | **PLANNED** |
| LED-06 | Non-deterministic inference hazard | User Req #14 | **P1** | Architecture risk | **YES** | Enforce fixed eval mode, no stochastic ops, and test identical output on repeat | `test_stgcn_model.py` | **PLANNED** |
| LED-07 | Mixing UNKNOWN into trained model classes | User Req #1 | **P1** | Architecture risk | **YES** | Limit trained model classes to 6; handle UNKNOWN/UNCERTAIN in `UncertaintyEvaluator` | `test_temporal_smoothing.py` | **PLANNED** |
| LED-08 | Coordinator bloat / orchestration tight coupling | User Req #5 | **P1** | Architecture risk | **YES** | Create dedicated `TemporalHARRuntime` encapsulating buffer, model, smoother, and translator | `test_har_fault_isolation.py` | **PLANNED** |
| LED-09 | Event bus flood from continuous activity frames | User Req #10 | **P1** | Database/bus risk | **YES** | Implement semantic phase translator emitting `START`, `UPDATE`, `CHANGE`, `END` | `test_temporal_smoothing.py` | **PLANNED** |
| LED-10 | Multi-person temporal state collision | User Req #11 | **P0** | Concurrency risk | **YES** | Key temporal buffer by `track_id` with explicit disappearance and recovery policy | `test_har_multi_person.py` | **PLANNED** |
| LED-11 | Hardcoded buffer hyper-parameters | User Req #6 | **P2** | Rigidity risk | **YES** | Make $T$, $S$, sampling rate, and timeouts configurable via `ActivityConfig` | `test_config.py` | **PLANNED** |
| LED-12 | Synthetic data presented as domain evidence | User Req #9 | **P1** | Scientific integrity | **YES** | Tag all synthetic samples with provenance; label results as proxy/validation | `test_dataset.py` | **PLANNED** |
| LED-13 | Telemetry WebSocket missing activity payload | HUD requirement | **P2** | Missing field | **YES** | Update `telemetry_ws.py` to broadcast `activities` and `top_activity` in `TELEMETRY_FRAME` | `test_api_health.py` | **PLANNED** |
| LED-14 | Cockpit HUD lacking action recognition display | UI requirement | **P2** | Static HUD | **YES** | Add HAR health indicator, Action Recognition HUD card, and canvas skeleton action labels | Frontend build & visual | **PLANNED** |
