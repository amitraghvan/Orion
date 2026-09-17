# ORION Installation & Setup Guide

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments (SIH26174)  
**Organization:** Indian Space Research Organisation (ISRO)  
**Date:** September 17, 2026  
**Status:** VERIFIED ON MACOS (ARM64) & LINUX (X86_64)  

---

## 1. System Requirements

### Hardware Requirements
- **Processor:** Intel Core i7 / AMD Ryzen 7 (8 cores) or Apple Silicon (M1/M2/M3/M4) or NVIDIA Jetson Orin (flight edge).
- **RAM:** 16 GB minimum (32 GB recommended).
- **VRAM / Unified Memory:** 8 GB unified memory (macOS) or 6 GB dedicated VRAM (NVIDIA GPU).
- **Storage:** 10 GB available SSD space (for weights, local recording buffers, and dataset).
- **Camera:** Standard USB 2.0/3.0 UVC webcam or CSI camera interface (640x480 to 1920x1080 @ 30 FPS).
- **Audio Output:** Standard audio device (speakers/headphones) for voice alert synthesis.

### Software Prerequisites
- **Operating System:** macOS 14+ (Sonoma/Sequoia) or Linux Ubuntu 22.04 LTS / 24.04 LTS.
- **Python:** Python 3.11 (strictly recommended: 3.11.x).
- **Package Manager:** `uv` (recommended) or standard `pip`.
- **Compiler (Optional for native SIMD acceleration):** Clang 15+ (macOS) or GCC 11+ with CMake 3.22+.

---

## 2. Standard Installation Workflow

### Step 1: Clone the Repository
```bash
git clone https://github.com/amitraghvan/Orion.git
cd Orion
```

### Step 2: Set Up Virtual Environment & Dependencies
Using `uv` (fastest and recommended):
```bash
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install -r requirements-dev.txt
```

Or using standard `python3.11`:
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Step 3: Run Environment Diagnostics
Verify all 7 subsystem components pass:
```bash
python scripts/doctor.py
```
Expected output:
```
📊 DOCTOR READINESS SCORE: 100.0% (7/7 checks passed)
🎉 Phase 0 Foundation is nominal and ready for development!
```

### Step 4: Verify Neural Network Model Weights
Ensure pretrained models exist in `models/weights/` and fine-tuned checkpoints in `models/bas_experiment/`:
```bash
ls -lh models/weights/*.pt models/bas_experiment/*.pt
```
Required weights:
- `models/weights/yolo11n.pt` (5.6 MB)
- `models/weights/yolo11n-pose.pt` (6.2 MB)
- `models/weights/stgcn_har_v1.pt` (1.9 MB)
- `models/bas_experiment/best.pt` (1.9 MB)

### Step 5: Execute Test Suite
Run the full test suite to guarantee zero regression:
```bash
pytest tests/
```
All 189 unit and integration tests should report **PASSED**.
