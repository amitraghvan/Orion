# ORION Air-Gapped Offline Operation & Edge Audit

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments (SIH26174)  
**Organization:** Indian Space Research Organisation (ISRO)  
**Date:** September 17, 2026  
**Status:** 100% AIR-GAPPED & OFFLINE CAPABLE (AUDITED)  

---

## 1. Executive Summary & Air-Gap Verification

Under SIH26174, the AI system **must operate as an offline standalone system** processing local camera feeds at the edge without external network or internet access.

The entire codebase has been forensically audited for external telemetry, analytics, cloud API calls, and remote downloads.

### Forensic Offline Assessment:

| Operational Dimension | Status | Forensic Evidence |
|---|---|---|
| **Runtime Execution** | **100% OFFLINE** | Zero network socket creation except local binding (`127.0.0.1`) |
| **Model Loading** | **100% OFFLINE** | All weights loaded strictly from local disk (`models/weights/`, `models/bas_experiment/`) |
| **Speech Synthesis (TTS)** | **100% OFFLINE** | Local OS speech engine (`say` / `pyttsx3` / `espeak`). Zero cloud TTS calls |
| **Data Storage** | **100% OFFLINE** | Local SQLite (`data/orion_dev.db`) and local filesystem MP4 files (`recordings/`) |
| **User Interface** | **100% OFFLINE** | Native PySide6 Qt GUI. Zero external CDN scripts, fonts, or web assets |
| **IP Video Streaming** | **LOCAL NETWORK ONLY** | Local HTTP server (`HTTPServer`) bound to local interface (`127.0.0.1:8080`) |
| **Model Training** | **100% OFFLINE** | PyTorch training loops execute on local GPU/MPS/CPU using local datasets |
| **Bootstrap Installation** | **OFFLINE READY** | Pre-packaged wheel bundles allow completely air-gapped installation |

---

## 2. Codebase Forensic Audit for External Calls

A comprehensive regex audit was executed across the codebase searching for external network calls and cloud providers:

| Search Pattern | Found Occurrences in Production Code | Status |
|---|---|---|
| `api.openai.com` | **0** | **CLEAN** |
| `generativelanguage.googleapis.com` (Gemini) | **0** | **CLEAN** |
| `api.groq.com` | **0** | **CLEAN** |
| `api.elevenlabs.io` | **0** | **CLEAN** |
| `huggingface.co` (Runtime downloads) | **0** | **CLEAN** |
| `wandb` (Weights & Biases cloud telemetry) | **0** | **CLEAN** |
| `requests.get` / `httpx.get` (Outbound) | **0** (Except local test client) | **CLEAN** |
| `cdn.jsdelivr.net` / `unpkg.com` | **0** | **CLEAN** |
| Google Fonts / External CSS | **0** | **CLEAN** |

---

## 3. Deployment on Air-Gapped Spaceflight Hardware

To deploy ORION onto an isolated flight compute node (e.g., inside an avionics rack or microgravity payload):

### 1. Offline Artifact Bundle Packaging
On an internet-connected development workstation:
```bash
# Download all required wheels to a local directory
mkdir -p offline_wheels
pip download -r requirements.txt -d offline_wheels/

# Package weights, configs, and application source
tar -czvf orion_airgap_bundle.tar.gz \
    offline_wheels/ \
    models/ \
    configs/ \
    app/ \
    ai/ \
    backend/ \
    data/ \
    scripts/ \
    launch.sh \
    run.py
```

### 2. Air-Gapped Flight Node Ingestion
On the air-gapped flight computer:
```bash
# Extract bundle
tar -xzvf orion_airgap_bundle.tar.gz
cd Orion/

# Create venv and install strictly from offline wheels
python3.11 -m venv .venv
source .venv/bin/activate
pip install --no-index --find-links=offline_wheels/ -r requirements.txt

# Run system doctor
python scripts/doctor.py

# Commense mission assistant
./launch.sh
```

---

## 4. Network Binding & Firewall Posture

- By default, ORION binds services strictly to `127.0.0.1` (loopback interface).
- If IP video streaming is required across the spacecraft's local LAN, `configs/settings.yaml` can be configured to bind `streaming.host: 0.0.0.0`.
- The application requires **zero inbound or outbound internet ports**. Inbound access can be restricted entirely to port 8080 (MJPEG stream) and port 8000 (optional telemetry API).
