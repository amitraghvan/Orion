# ORION Phase 1.5 — Model Provenance & License Audit
**SIH26174 | AI Human Activity Recognition for On-board BAS Experiments**  
**Date:** September 2026  
**Status:** Frozen & Approved for Air-Gapped / Edge Deployment

---

## 1. Executive Summary

Phase 1.5 introduces Human-Object Interaction (HOI), hand perception, target object detection, and multimodal evidence intelligence into the ORION runtime. As an air-gapped, offline-first system destined for spaceflight payload computing (e.g. ISRO BAS / Gaganyaan payloads), strict licensing and provenance compliance must be maintained.

All libraries, model architectures, weight formats, and spatial mathematics used in Phase 1.5 are audited below.

---

## 2. Model Provenance & Licensing Matrix

| Component | Architecture / Method | Weight Origin / Source | License | Edge / Air-Gapped Ready |
|---|---|---|---|---|
| **Person Detector** | YOLO11n | Ultralytics / PyTorch export | AGPL-3.0 / Enterprise | ✅ Yes (Local weights loaded via file hash) |
| **Object Detector** | YOLO11n Multi-Class | Ultralytics COCO / Fine-tuned BAS | AGPL-3.0 / Enterprise | ✅ Yes (Local weights loaded via file hash) |
| **Pose Estimator** | YOLO11n-pose (17 COCO Keypoints) | Ultralytics / PyTorch export | AGPL-3.0 / Enterprise | ✅ Yes (Local weights loaded via file hash) |
| **Hand Extractor** | Wrist-Keypoint Bounding Gating | Deterministic Kinematic Geometry | BSD-3-Clause (Custom ORION) | ✅ Yes (Zero weights, 100% deterministic) |
| **HOI Associator** | Bipartite Hungarian Matching | `scipy.optimize.linear_sum_assignment` | BSD-3-Clause | ✅ Yes (Zero neural weights, deterministic) |
| **Interaction State Machine** | 7-State Temporal Hysteresis | Deterministic Finite State Machine | MIT (ORION Core) | ✅ Yes (Zero neural weights, bounded memory) |
| **ST-GCN Temporal HAR** | Spatial-Temporal GCN (9-layer) | Custom PyTorch weights (BAS-HAR) | Apache 2.0 / BSD | ✅ Yes (Local checkpoint, offline inference) |
| **Multimodal Fusion Engine** | 4-Level Deterministic Fusion | Rule-based & Bayesian Dempster-Shafer | MIT (ORION Core) | ✅ Yes (Deterministic logic, no cloud dependencies) |

---

## 3. Dependency License Verification

| Package | Version | License | Usage in Phase 1.5 | Compliance Assessment |
|---|---|---|---|---|
| `torch` | >= 2.0.0 | Modified BSD | ST-GCN tensor computation and YOLO inference | Permissive, compatible with edge execution |
| `scipy` | >= 1.11.0 | BSD-3-Clause | Bipartite graph matching in HOI associator | Permissive, auditable numerical backend |
| `numpy` | >= 1.24.0 | BSD-3-Clause | Geometry, IoU calculation, array math | Permissive, industry standard |
| `pydantic` | >= 2.0.0 | MIT | Strict type contracts and validation schemas | Permissive, zero runtime licensing restrictions |
| `fastapi` | >= 0.100.0 | MIT | Telemetry API and WebSocket streaming | Permissive, local network only |
| `opencv-python` | >= 4.8.0 | Apache 2.0 | Frame ingestion, video replay, drawing | Permissive, compatible with edge execution |

---

## 4. Air-Gapped & Offline Verification

1. **No External Network Calls:**
   - Hand and object detection, bipartite matching, state machine tracking, and evidence fusion run 100% offline on CPU or local edge accelerators.
   - Zero telemetry, analytics, or external API pings are triggered.
2. **Model Weight Integrity:**
   - Weight files are cryptographically validated against SHA-256 hashes defined in `configs/models/registry.yaml` prior to instantiation.
   - Corrupted or modified weights trigger fail-safe execution rather than unsafe fallback.
3. **No Proprietary Cloud SDKs:**
   - Neither Google Cloud, AWS, nor Azure SDKs are bundled. System is 100% self-contained within the Python/Conda virtual environment.
