# ORION Documentation Forensic Audit

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments (SIH26174)  
**Organization:** Indian Space Research Organisation (ISRO)  
**Audit Date:** September 17, 2026  
**Auditor:** Principal Software Architect & Forensic Engineering Team  

---

## 1. Audit Methodology & Taxonomy

Every markdown and LaTeX document across the `docs/` tree has been forensically analyzed against:
1. Actual source code implementation in `ai/`, `backend/`, `app/`, and `cpp/`.
2. Actual runtime behavior verified during live camera and replay execution.
3. Actual model weights, manifests, training logs, and test suites.

### Disposition Classification
- **KEEP**: Accurate, active, authoritative, and aligned with implementation.
- **UPDATE**: Valuable historical or technical content requiring alignment with latest code reality.
- **MERGE**: Content has been consolidated into the canonical documentation hierarchy (`docs/architecture/`, `docs/ai/`, `docs/deployment/`, `docs/compliance/`, `docs/research/`).
- **ARCHIVE**: Superseded phase logs or point-in-time ledgers preserved for historical provenance.
- **DELETE**: Temporary scaffolds, empty templates, or conflicting duplicates.

---

## 2. Document-by-Document Forensic Matrix

| Document Path | Purpose | Status | Forensic Finding / Contradiction | Disposition Action |
|---|---|---|---|---|
| `docs/architecture.md` | General system architecture overview | UPDATE / MERGE | Mixes Web frontend concepts with Qt desktop; claims RTSP streaming while code uses HTTP MJPEG | Superseded by `docs/architecture/system-overview.md` |
| `docs/deployment.md` | Early deployment notes | MERGE | Outdated instructions referencing unmanaged venv and missing Qt dependencies | Superseded by `docs/deployment/installation.md` |
| `docs/inference.md` | Perception inference guide | UPDATE / MERGE | Describes ST-GCN and YOLO inference accurately but lacks runtime decoupling details | Superseded by `docs/ai/inference.md` |
| `docs/performance.md` | Early latency targets | UPDATE / MERGE | Contains theoretical latency targets without empirical benchmark data | Superseded by `docs/performance/benchmark.md` |
| `docs/production_deployment.md` | Production air-gapped guidelines | KEEP / MERGE | Good flight security guidelines, needs alignment with `launch.sh` and PySide6 | Consolidated into `docs/deployment/production-deployment.md` |
| `docs/SIH_REQUIREMENTS.md` | SIH26174 official problem statement breakdown | KEEP / MERGE | Accurate requirements, but lacks implementation evidence matrix | Superseded by `docs/compliance/SIH26174-compliance.md` |
| `docs/troubleshooting.md` | Common errors and resolutions | KEEP | Valid troubleshooting tips for camera handle contention and MPS fallback | Retained as operational reference |
| `docs/BAS_EXPERIMENT_DATASET_GUIDE.md` | Guide to BAS real dataset ingestion | KEEP / MERGE | Accurate description of 20 video recordings in `BAS_REAL_DATA` | Consolidated into `docs/ai/dataset.md` |
| `docs/BAS_EXPERIMENT_FRONTEND_GUIDE.md` | Legacy React frontend guide | ARCHIVE | Describes legacy React/Tailwind cockpit; current primary interface is Qt native desktop | Archived as legacy interface documentation |
| `docs/phase_1_3_architecture.md` | Phase 1.3 Temporal HAR architecture | ARCHIVE | Accurate point-in-time design for ST-GCN integration | Archived as Phase 1.3 milestone record |
| `docs/phase_1_3_audit.md` | Phase 1.3 frozen audit | ARCHIVE | Forensic ledger of Phase 1.3 perception layer | Archived as Phase 1.3 milestone record |
| `docs/phase_1_3_change_ledger.md` | Phase 1.3 commits & edits | ARCHIVE | Implementation delta log | Archived as Phase 1.3 milestone record |
| `docs/phase_1_3_temporal_har.md` | ST-GCN mathematical & graph formulation | MERGE | High-value technical math on spatial-temporal graph adjacency | Consolidated into `docs/ai/temporal-har.md` |
| `docs/phase_1_4_architecture.md` | Protocol state machine design | ARCHIVE | Accurate design of protocol decision engine and FSM | Consolidated into `docs/architecture/experiment-state-machine.md` |
| `docs/phase_1_4_audit.md` | Phase 1.4 frozen audit | ARCHIVE | Verification of protocol engine components | Archived as Phase 1.4 milestone record |
| `docs/phase_1_4_change_ledger.md` | Phase 1.4 delta ledger | ARCHIVE | Implementation delta log | Archived as Phase 1.4 milestone record |
| `docs/phase_1_4_protocol_engine.md` | Protocol evaluation rules | MERGE | Detailed sequence validation rules | Consolidated into `docs/architecture/experiment-state-machine.md` |
| `docs/phase_1_4_replay_scenarios.md` | Replay test specifications | KEEP / MERGE | Valid test scenarios for valid, out-of-order, and skipped steps | Consolidated into `docs/testing/test-strategy.md` |
| `docs/phase_1_4_validation.md` | Protocol engine test validation | KEEP / MERGE | Test verification results | Consolidated into `docs/testing/validation-results.md` |
| `docs/phase_1_5_architecture.md` | Multimodal HOI architecture | ARCHIVE | Accurate design of hand perception and interaction state machine | Consolidated into `docs/architecture/ai-pipeline.md` |
| `docs/phase_1_5_audit.md` | Phase 1.5 frozen audit | ARCHIVE | Reusable vs missing component inventory | Archived as Phase 1.5 milestone record |
| `docs/phase_1_5_change_ledger.md` | Phase 1.5 delta ledger | ARCHIVE | Implementation delta log | Archived as Phase 1.5 milestone record |
| `docs/phase_1_5_license_audit.md` | Third-party dependency license audit | KEEP | Critical air-gapped compliance analysis (Ultralytics AGPL-3.0, PySide6 LGPL-3.0) | Retained as operational compliance reference |
| `docs/architecture/adr_001` through `adr_015` | 15 Architectural Decision Records | KEEP | High-value architectural rationale for monorepo, capture threads, ST-GCN, FSM, and HOI | Retained in `docs/architecture/` as active ADRs |
| `docs/architecture/c4_model.md` | C4 architecture diagrams | KEEP / MERGE | Valid system context and container definitions | Incorporated into `docs/architecture/system-overview.md` |
| `docs/architecture/offline_first_design.md` | Air-gapped offline constraints | KEEP / MERGE | Authoritative specification of zero external network calls | Incorporated into `docs/deployment/offline-operation.md` |
| `docs/research/benchmark_research_template.md` | Empty template | DELETE / SUPERSEDED | 627-byte scaffold | Replaced by canonical `docs/research/technical-research.md` |
| `docs/research/computer_vision_template.md` | Empty template | DELETE / SUPERSEDED | 812-byte scaffold | Replaced by canonical `docs/research/technical-research.md` |
| `docs/research/dataset_research_template.md` | Empty template | DELETE / SUPERSEDED | 424-byte scaffold | Replaced by canonical `docs/research/technical-research.md` |
| `docs/research/edge_ai_template.md` | Empty template | DELETE / SUPERSEDED | 611-byte scaffold | Replaced by canonical `docs/research/technical-research.md` |
| `docs/research/experiment_validation_template.md` | Empty template | DELETE / SUPERSEDED | 433-byte scaffold | Replaced by canonical `docs/research/technical-research.md` |
| `docs/research/hoi_interaction_template.md` | Empty template | DELETE / SUPERSEDED | 451-byte scaffold | Replaced by canonical `docs/research/technical-research.md` |
| `docs/research/microgravity_ai_template.md` | Empty template | DELETE / SUPERSEDED | 530-byte scaffold | Replaced by canonical `docs/research/technical-research.md` |
| `docs/research/model_comparison_template.md` | Empty template | DELETE / SUPERSEDED | 574-byte scaffold | Replaced by canonical `docs/research/technical-research.md` |
| `docs/research/pose_estimation_template.md` | Empty template | DELETE / SUPERSEDED | 644-byte scaffold | Replaced by canonical `docs/research/technical-research.md` |
| `docs/research/temporal_har_template.md` | Empty template | DELETE / SUPERSEDED | 592-byte scaffold | Replaced by canonical `docs/research/technical-research.md` |
| `docs/research_paper/RESEARCH_PAPER.md` | Academic conference paper draft | KEEP / MERGE | Comprehensive research paper on spatial-temporal graph convolutional networks for BAS experiments | Consolidated into canonical `docs/research/research-paper.md` |
| `docs/research_paper/CLAIM_EVIDENCE_MATRIX.md` | Academic claim verification | KEEP | Rigorous verification of all scientific claims against repository artifacts | Retained in research archive |
| `docs/research_paper/DATASET_AUDIT.md` | Comprehensive BAS dataset audit | KEEP / MERGE | Full forensic metadata on all 20 videos | Consolidated into `docs/ai/dataset.md` |
| `docs/research_paper/EXPERIMENTAL_EVIDENCE.md` | Evidence records | KEEP / MERGE | Exact numbers on loss, accuracy, and latency | Consolidated into `docs/ai/training.md` & `docs/performance/benchmark.md` |
| `docs/research_paper/LIMITATIONS_AND_FUTURE_WORK.md` | Scientific limitations | KEEP / MERGE | Critical gaps (overfitting, 3D mesh recovery) | Consolidated into `docs/research/research-gaps.md` |
| `docs/research_paper/REFERENCES.bib` | BibTeX bibliography | KEEP | 25+ academic citations (ST-GCN, YOLOv8/11, ByteTrack, etc.) | Retained in research archive |
| `docs/research_paper/REPOSITORY_RESEARCH_AUDIT.md` | Exhaustive research audit | KEEP | Forensic exploration of literature | Consolidated into `docs/research/literature-review.md` |
| `docs/research_paper/paper.tex` | IEEE/ACM LaTeX paper template | KEEP | Formatted conference submission | Retained in research archive |
| `docs/testing/aerospace_verification_strategy.md` | Verification standards | KEEP / MERGE | NASA/ESA DO-178C alignment principles | Consolidated into `docs/testing/test-strategy.md` |
| `docs/security/threat_model.md` | STRIDE air-gapped threat model | KEEP / MERGE | Spacecraft physical & local network security | Consolidated into `docs/security/security-audit.md` |
| `docs/deployment/air_gapped_station_deployment.md` | Deployment checklist | KEEP / MERGE | Installation protocol for isolated compute | Consolidated into `docs/deployment/offline-operation.md` |
| `docs/api/openapi_spec.md` | REST API documentation | KEEP | Documents FastAPI endpoints | Retained as API reference |
| `docs/api/websocket_telemetry_protocol.md` | Telemetry wire format | KEEP | Documents binary/JSON WebSocket framing | Retained as API reference |
| `docs/dataset/curation_protocol.md` | Video recording protocol | KEEP | Instructions for filming BAS experiment stages | Retained as dataset reference |
| `docs/hardware/spacecraft_avionics_interface.md` | Avionics hardware spec | KEEP | Hardware power and USB/CSI camera constraints | Retained as hardware reference |
| `docs/coding-standards/scientific_coding_standards.md` | Coding standards | KEEP | Type safety, determinism, and zero-allocation loops | Retained as engineering reference |

---

## 3. Summary of Structural Reorganization

To establish a unified, non-redundant, single-source-of-truth documentation hierarchy, all documents are structured into the canonical directories:
- `docs/architecture/`: Core system diagrams, runtime flows, state machines, and ADRs.
- `docs/ai/`: Truthful inventory of models, datasets, training regimes, and temporal HAR.
- `docs/compliance/`: Rigorous requirement-by-requirement SIH26174 matrix and traceability.
- `docs/deployment/`: Clean offline installation, configuration, and station deployment guides.
- `docs/testing/`: Verified test strategy, smoke tests, replay runs, and automated results.
- `docs/performance/`: Measured benchmarks for CPU, MPS, memory, and throughput.
- `docs/security/`: Air-gapped threat models, input validation, and copyleft risk mitigation.
- `docs/research/`: Peer-reviewed literature review, deep research gaps, and consolidated academic paper.
