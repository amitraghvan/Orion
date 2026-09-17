# ORION Documentation Library (Master Sequential Index)

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments  
**Problem Statement:** Smart India Hackathon 2026 | **SIH26174**  
**Organization:** Indian Space Research Organisation (ISRO)  
**Theme:** Space Technology  
**Classification:** Authoritative Sequential Documentation  

---

## Master Sequential Table of Contents

All project documentation is structured in strict sequential order from system architecture through AI models, compliance, deployment, testing, benchmarks, security, and scientific research. All legacy, superseded, and redundant phase ledgers have been consolidated into `09-archive/`.

```
docs/
├── README.md                          # ◄ This Master Index
├── SIH26174_GAP_ANALYSIS.md           # Master SIH26174 Gap Analysis & Research Roadmap
├── AUDIT_REPORT.md                    # Master Forensic Technical Audit
├── repository-map.md                  # Comprehensive File-by-File Codebase Map
├── documentation-audit.md             # Forensic Document Classification Ledger
│
├── 01-architecture/                   # SECTION 1: System Architecture & Data Flow
│   ├── 01_system-overview.md          # End-to-end system architecture & ASCII diagrams
│   ├── 02_runtime-flow.md             # Runtime execution traces, lifecycle & entrypoints
│   ├── 03_ai-pipeline.md              # 15-stage perception DAG (YOLO, Pose, HOI, ST-GCN)
│   ├── 04_experiment-state-machine.md # Formal 11-state FSM, sequence rules & skip logic
│   ├── 05_event-system.md             # In-memory pub/sub EventBus & 16 domain events
│   ├── 06_video-pipeline.md           # Capture thread, MP4 recorder & HTTP MJPEG stream
│   ├── 07_voice-alert-system.md       # Offline TTS annunciator & priority suppression
│   ├── 08_architecture-gap-analysis.md# Current vs. required architectural comparison
│   └── decisions/                     # Active Architectural Decision Records (ADR 001-015)
│
├── 02-ai/                             # SECTION 2: AI Models, Datasets & Kinematics
│   ├── 01_model-inventory.md          # Verified checkpoints, SHA-256 hashes & parameters
│   ├── 02_dataset.md                  # BAS experiment dataset audit & curation protocol
│   ├── 03_training.md                 # ST-GCN training logs, loss curves & evaluation
│   ├── 04_inference.md                # Multi-backend inference (Apple MPS, CUDA, CPU)
│   └── 05_temporal-har.md             # ST-GCN mathematical graph formulations & tensor math
│
├── 03-compliance/                     # SECTION 3: SIH26174 Official Compliance
│   ├── 01_SIH26174-compliance.md      # Requirement-by-requirement verification matrix
│   └── 02_traceability-matrix.md      # End-to-end code, class, test & artifact mapping
│
├── 04-deployment/                     # SECTION 4: Deployment & Air-Gapped Setup
│   ├── 01_installation.md             # Step-by-step developer & operator setup guide
│   ├── 02_configuration.md            # Pydantic v2 layered configuration & env overrides
│   ├── 03_offline-operation.md        # 100% air-gapped audit & zero-network verification
│   └── 04_production-deployment.md    # Systemd service units & containerized deployment
│
├── 05-testing/                        # SECTION 5: Verification & Quality Assurance
│   ├── 01_test-strategy.md            # Multi-tiered aerospace verification plan (DO-178C)
│   └── 02_validation-results.md       # Full automated test run (205/205 tests passing)
│
├── 06-performance/                    # SECTION 6: Empirical Benchmarks & Profiling
│   └── 01_benchmark.md                # Measured CPU, MPS, and FSM latency benchmarks
│
├── 07-security/                       # SECTION 7: Security & Vulnerability Analysis
│   └── 01_security-audit.md           # STRIDE threat model, input sanitization & licenses
│
├── 08-research/                       # SECTION 8: Research Literature & Academic Paper
│   ├── 01_literature-review.md        # Survey across 22 scientific & aerospace domains
│   ├── 02_technical-research.md       # Deep learning trade studies & HOI geometric math
│   ├── 03_research-gaps.md            # Scientific gap analysis on dataset scale & 3D HMR
│   └── 04_research-paper.md           # Full academic research paper for conference submission
│
└── 09-archive/                        # SECTION 9: Historical Provenance Archive
    ├── legacy_phases/                 # Phase 1.3, 1.4, 1.5 audits, change ledgers & notes
    ├── research_paper/                # Pre-consolidation research paper drafts & bibtex
    ├── dataset/                       # Early standalone dataset curation notes
    ├── hardware/                      # Standalone avionics interface drafts
    ├── coding-standards/              # Standalone coding guidelines
    └── api/                           # Standalone API specifications
```

---

## Sequential Reading Guide

1. **For Project Overview & Requirements:** Start with [`AUDIT_REPORT.md`](file:///Users/amitkumar/Orion/docs/AUDIT_REPORT.md) and [`03-compliance/01_SIH26174-compliance.md`](file:///Users/amitkumar/Orion/docs/03-compliance/01_SIH26174-compliance.md).
2. **For Software Engineers:** Read [`01-architecture/01_system-overview.md`](file:///Users/amitkumar/Orion/docs/01-architecture/01_system-overview.md) and [`01-architecture/02_runtime-flow.md`](file:///Users/amitkumar/Orion/docs/01-architecture/02_runtime-flow.md).
3. **For AI/CV Researchers:** Review [`02-ai/01_model-inventory.md`](file:///Users/amitkumar/Orion/docs/02-ai/01_model-inventory.md), [`02-ai/05_temporal-har.md`](file:///Users/amitkumar/Orion/docs/02-ai/05_temporal-har.md), and [`08-research/04_research-paper.md`](file:///Users/amitkumar/Orion/docs/08-research/04_research-paper.md).
4. **For DevOps & Spacecraft Integration:** Follow [`04-deployment/01_installation.md`](file:///Users/amitkumar/Orion/docs/04-deployment/01_installation.md) and [`04-deployment/03_offline-operation.md`](file:///Users/amitkumar/Orion/docs/04-deployment/03_offline-operation.md).
5. **For QA & Verification Leads:** Inspect [`05-testing/01_test-strategy.md`](file:///Users/amitkumar/Orion/docs/05-testing/01_test-strategy.md) and [`05-testing/02_validation-results.md`](file:///Users/amitkumar/Orion/docs/05-testing/02_validation-results.md).
