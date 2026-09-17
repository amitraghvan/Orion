# REPRODUCIBILITY GUIDE: ORION — BAS AI COPILOT
**Document ID:** ORION-REPRO-2026-011  
**Classification:** Research Reproducibility Specification  
**Date:** September 2026  
**Repository Path:** `/Users/amitkumar/Orion`  
**SIH Problem Statement:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments  

---

## 1. Environment & Software Stack Specification

To guarantee deterministic reproduction of all reported metrics, latency benchmarks, and protocol validations, the software environment must match the following parameters:

### Host Operating System:
- **Operating System:** macOS (Darwin 23.x / Apple Silicon ARM64) or Linux (Ubuntu 22.04 LTS x86_64 / ARM64)
- **POSIX Shell:** zsh or bash

### Core Runtime Runtimes:
- **Python Version:** `3.11.8` (Tested on `>=3.11,<3.12` per `pyproject.toml`)
- **Node.js Runtime:** `v20.15.0+`
- **Package Manager:** Python `uv` / `pip` (Wheel packaging via `hatchling`); Frontend `npm` (`10.7.0+`)

### Pinned Python Dependencies (`pyproject.toml`):
- `torch==2.2.2`
- `torchvision==0.17.2`
- `ultralytics==8.3.0`
- `opencv-python==4.11.0.86`
- `numpy==1.26.4`
- `scipy==1.14.1`
- `fastapi==0.115.0`
- `pydantic==2.10.3`
- `pydantic-settings==2.7.0`
- `uvicorn[standard]==0.34.0`
- `sqlalchemy[asyncio]==2.0.36`
- `aiosqlite==0.20.0`
- `structlog==24.4.0`
- `pytest==8.3.4`
- `pytest-asyncio==0.25.0`

### Pinned Frontend Dependencies (`frontend/package.json`):
- `react==18.3.1`
- `react-dom==18.3.1`
- `vite==5.4.2`
- `typescript==5.5.3`
- `tailwindcss==3.4.11`
- `zustand==4.5.5`
- `lucide-react==0.441.0`

---

## 2. Model Checkpoints & Cryptographic Provenance

All model weights are stored in `models/` with immutable SHA256 integrity checksums:

| Model Identifier | File Path | Framework | Input Shape | SHA256 Checksum |
| :--- | :--- | :--- | :---: | :--- |
| **YOLO11n Detector** | `models/weights/yolo11n.pt` | TorchScript | $(1, 3, 640, 640)$ | `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1` |
| **YOLO11n-Pose Estimator**| `models/weights/yolo11n-pose.pt` | TorchScript | $(1, 3, 640, 640)$ | `869e83fcdffdc7371fa4e34cd8e51c838cc729571d1635e5141e3075e9319dc0` |
| **ST-GCN HAR (Synthetic)**| `models/weights/stgcn_har_v1.pt` | PyTorch | $(B, 4, 32, 17)$ | `41570e8d4471b6596abe459fd93c6f34546c0059d974e0629dc886451a3e95ed` |
| **BAS-HAR-v1.0 (Real)** | `models/bas_experiment/best.pt` | PyTorch | $(B, 4, 32, 17)$ | `6d97fd61484bab97c978c5c946fbb7360a3574d00337faa3c4d62973d5f29b97` |

---

## 3. Step-by-Step Reproduction Workflow

### Step 1: Environment Setup
```bash
# Clone or navigate to repository root
cd /Users/amitkumar/Orion

# Create virtual environment and activate
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies in editable mode
pip install -e ".[dev,test,profiling]"

# Verify execution environment
python scripts/verify_environment.py
```

### Step 2: Programmatic Dataset Audit
Audits all 20 raw MP4 videos in `/Users/amitkumar/Downloads/BAS_REAL_DATA`:
```bash
python scripts/audit_bas_dataset.py
# Output: datasets/bas_experiment/reports/raw_data_audit.json
# Output: datasets/bas_experiment/reports/raw_data_audit.md
```

### Step 3: Feature Extraction & Sequence Windowing
Extracts 1,374 temporal feature arrays of shape `(4, 32, 17)` across train, val, and test splits:
```bash
python scripts/prepare_bas_dataset.py
# Output: datasets/bas_experiment/sequences/train/*.npz (473 files)
# Output: datasets/bas_experiment/sequences/val/*.npz (230 files)
# Output: datasets/bas_experiment/sequences/test/*.npz (671 files)
# Output: datasets/bas_experiment/metadata/splits.json
```

### Step 4: ST-GCN Model Training & Checkpoint Generation
Trains the 4-block ST-GCN on Subjects `SP01` and `SP02` for 25 epochs:
```bash
python scripts/train_bas_har.py
# Output: models/bas_experiment/best.pt (Epoch 8 checkpoint)
# Output: models/bas_experiment/last.pt (Epoch 25 checkpoint)
# Output: models/bas_experiment/metrics.json
```

### Step 5: Quantitative Evaluation on Held-Out Test Data
Evaluates the model against held-out subject `SP04` and 3 anomaly clips:
```bash
python scripts/evaluate_bas_har.py
# Output: models/bas_experiment/evaluation.json
# Output: models/bas_experiment/confusion_matrix.png
```

### Step 6: Perception & Protocol Latency Benchmarks
Executes end-to-end perception pipeline profiling and protocol engine stress testing:
```bash
# Perception & HAR pipeline benchmark (60 frames)
python scripts/benchmark_perception.py

# Protocol decision engine throughput benchmark (10,000 events)
python scripts/benchmark_protocol_engine.py
```

### Step 7: Automated Test Suite Verification
Runs the comprehensive unit, integration, and contract test suite:
```bash
pytest -v tests/
# Expected: 83 passed in ~5.5 seconds
```

### Step 8: Full End-to-End System Launch
```bash
# Terminal 1: Launch Backend API and WebSocket Gateway
uvicorn orion.api.app:create_app --factory --host 0.0.0.0 --port 8000

# Terminal 2: Launch React Cockpit Frontend
cd frontend
npm install
npm run dev
# Cockpit accessible at: http://localhost:5173
```
