# 🛰️ ORION BAS AI Copilot (`orion-bas-ai`)

[![CI Pipeline](https://github.com/isro-bas/orion-bas-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/isro-bas/orion-bas-ai/actions/workflows/ci.yml)
[![Security Scan](https://github.com/isro-bas/orion-bas-ai/actions/workflows/security.yml/badge.svg)](https://github.com/isro-bas/orion-bas-ai/actions/workflows/security.yml)
[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![Strict Typing](https://img.shields.io/badge/mypy-strict-success.svg)](https://mypy.readthedocs.io/)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License](https://img.shields.io/badge/license-Proprietary%20%2F%20ISRO--BAS-orange.svg)]()

> **Offline AI Human Activity Recognition System for Bharatiya Antariksh Station (BAS) Experiments.**
> Built to flight-software standards of ISRO HSFC, NASA JPL, ESA Space Robotics, and SpaceX Flight Software.

---

## 🌌 1. Vision & Mission

The **ORION BAS AI Copilot** is an air-gapped, zero-cloud, deterministic Edge AI infrastructure designed to assist astronauts and ground researchers aboard the **Bharatiya Antariksh Station (BAS)**.

During long-duration orbital microgravity experiments (e.g. fluid physics, crystal growth, cellular biology, robotics maintenance), crew attention is a scarce and vital resource. ORION monitors experimental workstations via high-speed optical sensors, verifies procedural steps, detects human-object interactions (HOI), tracks tool usage, assesses temporal human activities, and annunciates safety alerts in real time — completely offline without relying on Earth telemetry links.

---

## 🏛️ 2. Architectural Overview

```
                          ┌─────────────────────────────┐
                          │     High-Speed Optical      │
                          │   Glovebox Sensor (GigE)    │
                          └──────────────┬──────────────┘
                                         │ Raw Video Frames
                                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   ORION Edge Perception Runtime                        │
│                                                                        │
│   ┌────────────────┐      ┌────────────────┐      ┌────────────────┐   │
│   │ 2D/3D Object   │─────▶│  17/133 Pose   │─────▶│  Spatial-Temp  │   │
│   │   Detection    │      │   Estimation   │      │ HOI & Activity │   │
│   └────────────────┘      └────────────────┘      └────────────────┘   │
│           │                       │                       │            │
│           └───────────────────────┼───────────────────────┘            │
│                                   ▼                                    │
│                    ┌─────────────────────────────┐                     │
│                    │   Experiment State Graph    │                     │
│                    │     (Deterministic HSM)     │                     │
│                    └──────────────┬──────────────┘                     │
└───────────────────────────────────┼────────────────────────────────────┘
                                    │ Telemetry Events
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 FastAPI Async-First Mission Backend                    │
│                                                                        │
│   ┌────────────────┐      ┌────────────────┐      ┌────────────────┐   │
│   │ Typed Event    │      │  SQLAlchemy 2  │      │ Offline Audio  │   │
│   │      Bus       │      │  Telemetry DB  │      │ Priority Queue │   │
│   └────────────────┘      └────────────────┘      └────────────────┘   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ WebSocket / LAN Multicast
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             Air-Gapped React / Tailwind Mission Control UI             │
│            (Low-Latency Telemetry HUD & Experiment Protocol)           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 3. Repository Map

```
orion-bas-ai/
├── .devcontainer/         # VSCode devcontainer specification (Python 3.11, Node 22, uv)
├── .github/               # CI pipelines, issue templates, PR template, CODEOWNERS
├── ai/                    # Perception package architecture (14 modular domain packages)
│   └── src/orion_ai/      # Camera, Detection, Tracking, Pose, Activity, HOI, Inference, etc.
├── assets/                # Architectural diagrams, station schemas, audio chimes
├── backend/               # FastAPI async mission backend, SQLAlchemy 2 ORM models, Alembic
│   └── src/orion/         # Core, DB, Hardware Abstraction, Health, Recording, Audio, API
├── configs/               # Layered configuration system (base, dev, test, staging, prod, hardware)
├── datasets/              # Scientific dataset platform (COCO, YOLO, CVAT, Label Studio, MMPose)
├── deployment/            # Docker multi-stage images, Docker Compose profiles, systemd units
├── docs/                  # Aerospace documentation system (Architecture, Research, Security, Standards)
├── experiments/           # Configurable BAS experiment YAML templates and Pydantic schemas
├── frontend/              # Air-gapped React 18/19, TypeScript, Vite, Tailwind dark theme tokens
├── infrastructure/        # Observability templates (Prometheus, Grafana, OpenTelemetry)
├── scripts/               # System automation & diagnostic suite (doctor, verify_environment, etc.)
├── tests/                 # Strict pytest suite (Unit, Integration, Contract, Performance)
├── tools/                 # Benchmarking and profiling wrappers (cProfile, PyInstrument)
├── pyproject.toml         # Unified dependency manifest & quality toolchain configuration
├── requirements.txt       # Legacy pip compatibility fallback
└── README.md              # This document
```

---

## ⚡ 4. Installation & Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 22.04 / 24.04 LTS / Debian 12 / RHEL 9) or macOS (Apple Silicon M-series)
- **Python**: `3.11.x` (Mandatory runtime)
- **Node.js**: `v22.x LTS` & `npm >= 10`
- **Package Manager**: [`uv`](https://github.com/astral-sh/uv) (v0.5+)

### Quickstart Setup

```bash
# 1. Clone the repository
git clone https://github.com/isro-bas/orion-bas-ai.git
cd orion-bas-ai

# 2. Bootstrap virtual environment with uv (Python 3.11)
uv venv --python 3.11 .venv
source .venv/bin/activate

# 3. Synchronize dependencies in editable mode
uv pip install -e ".[all]"

# 4. Install frontend dependencies
npm install --prefix frontend
```

---

## 🛠️ 5. Development Setup & Commands

All development operations are automated via dedicated CLI scripts under `scripts/`:

```bash
# Run comprehensive system diagnostics (Python 3.11, CUDA/Metal, storage, camera)
python scripts/doctor.py

# Verify local environment compliance against aerospace specifications
python scripts/verify_environment.py

# Execute full test suite
python scripts/test.py

# Run static analysis and linting (Ruff)
python scripts/lint.py

# Format code (Ruff + Prettier)
python scripts/format.py

# Probe GPU accelerator status (NVIDIA CUDA / Apple MPS)
python scripts/check_gpu.py

# Clean build artifacts, pycache, and temporary logs
python scripts/clean.py
```

---

## 🛡️ 6. Quality & Strict Typing Toolchain

Every pull request must pass the automated aerospace quality gate:

| Tool | Purpose | Command |
|---|---|---|
| **Ruff** | Ultra-fast linter & style enforcement | `uv run ruff check .` |
| **Ruff Format** | Deterministic code formatting | `uv run ruff format --check .` |
| **Mypy** | Strict type-checking (`disallow_untyped_defs = true`) | `uv run mypy backend/src ai/src datasets/src` |
| **Bandit** | AST security vulnerability scanner | `uv run bandit -r backend/src ai/src` |
| **Pytest** | Async test suite with branch coverage | `uv run pytest -v tests/` |

---

## 🔒 7. Security & Air-Gapped Operation

- **Zero Telemetry Leakage**: No external telemetry endpoints or phone-home analytics are configured.
- **Path Traversal Sandboxing**: The `orion.core.security` module enforces containment inside designated directories.
- **Cryptographic Verification**: Every model weights artifact and dataset split is verified against SHA-256 digests.
- **Secret Masking**: No raw credentials or encryption keys are logged to console or exported telemetry streams.

---

## 🚀 8. Roadmap & Phase Progression

- **Phase 0 (Current)**: Scientific production foundation, architecture, type-safe interfaces, environment configs, quality toolchains.
- **Phase 1**: Camera frame acquisition engine, V4L2/GigE pipeline, and ONNX Runtime edge inference harness.
- **Phase 2**: Real-time crew detection (YOLO11x) and MMPose skeleton keypoint extraction in microgravity.
- **Phase 3**: Spatio-temporal Human-Object Interaction (HOI) reasoning and temporal action recognition.
- **Phase 4**: Automated BAS Experiment State Machine validation and astronaut cockpit alert annunciation.
- **Phase 5**: Hardware-in-the-loop (HITL) flight qualification testbed at ISRO HSFC.

---

## 📜 9. Contribution & Licensing

Contribution is restricted to authorized consortium partners and research fellows. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) for vulnerability disclosure procedures.

**Copyright (c) 2026 Bharatiya Antariksh Station AI Consortium / ISRO HSFC. All rights reserved.**
