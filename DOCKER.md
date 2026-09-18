# ORION BAS AI Copilot — Container & Docker Guide

[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![DevContainer](https://img.shields.io/badge/DevContainer-Supported-blue?style=flat-square&logo=visualstudiocode)](https://containers.dev/)
[![Air-Gapped](https://img.shields.io/badge/Air--Gapped-100%25%20Offline-success?style=flat-square)]()
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)

This guide details how to build, run, and develop **ORION: AI Human Activity Recognition for Bharatiya Antariksh Station (BAS) Experiments** inside Docker containers.

The container environment is engineered for **instant reproducibility**: anyone who forks or clones this repository can start the entire perception pipeline, REST API, WebSocket telemetry, and live video stream with a **single command**, requiring zero manual configuration.

---

## ⚡ 1-Minute Quickstart ("Fork & Run")

### Step 1: Clone or Fork the Repository
```bash
git clone https://github.com/amitraghvan/Orion.git
cd Orion
```

### Step 2: Launch with Docker Compose
```bash
docker compose up
```

That's it! Docker builds the container, initializes the database, loads the pretrained YOLO and ST-GCN models, starts looping the bundled experiment replay video, and exposes all network services.

---

## 🌐 Endpoints & Web Interfaces

Once `docker compose up` is running, open the following in your browser:

| Interface | URL | Description |
|---|---|---|
| **Live Camera HUD** | [`http://localhost:8080/live`](http://localhost:8080/live) | Real-time multipart MJPEG video stream showing detections & bounding boxes. |
| **Interactive API Docs** | [`http://localhost:8000/docs`](http://localhost:8000/docs) | Swagger UI for exploring and testing REST API endpoints. |
| **System Health Check** | [`http://localhost:8000/api/v1/health/live`](http://localhost:8000/api/v1/health/live) | Liveness diagnostic endpoint (`status: OK`). |
| **WebSocket Telemetry** | `ws://localhost:8000/ws/telemetry` | Real-time JSON telemetry stream of domain events and FSM state changes. |
| **Prometheus Metrics** | [`http://localhost:9090/metrics`](http://localhost:9090/metrics) | In-flight latency, frame rates, and activity confidence metrics. |

---

## 🛠️ CLI Operations Inside Docker

You can run diagnostic, testing, and smoke-testing commands directly through the container without creating a local virtual environment:

### Run Diagnostic Health Check
```bash
docker compose run --rm orion doctor
```
*Executes `scripts/doctor.py` inside the container, verifying Python 3.11 runtime, `uv`, configs, persistence engine, and directory layout.*

### Run Unit Test Suite
```bash
docker compose run --rm orion test
```
*Executes `pytest tests/unit` with asyncio and hypothesis fixtures.*

### Run Perception Video Replay Smoke Test
```bash
docker compose run --rm orion smoke
```
*Loads `assets/sample_replay.mp4`, executes object detection, pose estimation, hand-object interaction (HOI), and protocol FSM validation for 40 frames.*

### Interactive Shell
```bash
docker compose run --rm orion bash
```
*Spawns an interactive bash shell inside the fully provisioned Debian environment with Python 3.11 and all models.*

---

## 📊 Full Observability Stack (Prometheus + Grafana + OTel)

To launch ORION alongside Prometheus metrics scraping, Grafana dashboards, and OpenTelemetry collector, use the `observability` profile:

```bash
docker compose --profile observability up
```

Additional service endpoints:
- **Grafana Dashboard:** [`http://localhost:3001`](http://localhost:3001) (Default credentials: `admin` / `admin`)
- **Prometheus UI:** [`http://localhost:9091`](http://localhost:9091)
- **OpenTelemetry Collector:** `localhost:4317` (gRPC) / `localhost:4318` (HTTP)

---

## 💻 GitHub Codespaces & VS Code Dev Containers

ORION includes complete configuration for **GitHub Codespaces** and **VS Code Remote - Containers** (`.devcontainer/`):

1. **GitHub Codespaces:**
   - In your forked GitHub repository, click **Code** → **Codespaces** tab → **Create codespace on main**.
   - Codespaces will automatically build the container, configure Python 3.11, install all packages using `uv`, run the doctor diagnostic, and forward ports `8000`, `8080`, and `9090`.

2. **VS Code Dev Containers (Local):**
   - Open the repository folder in VS Code.
   - When prompted with *"Folder contains a Dev Container configuration file. Reopen in Container?"*, click **Reopen in Container** (or press `F1` → `Remote-Containers: Reopen in Container`).

---

## 🚀 Standalone Docker Commands (Without Compose)

If you prefer using pure Docker commands:

```bash
# Build the image
docker build -t orion:latest .

# Run container with ports and persistence mounts
docker run -d \
  --name orion-copilot \
  -p 8000:8000 \
  -p 8080:8080 \
  -p 9090:9090 \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/logs:/app/logs" \
  -v "$(pwd)/recordings:/app/recordings" \
  orion:latest

# Check container logs
docker logs -f orion-copilot

# Stop container
docker stop orion-copilot
```

---

## 🎮 GPU & Hardware Acceleration (NVIDIA CUDA)

By default, the container runs on **CPU** with SIMD optimization, ensuring compatibility across all machines.

To run with **NVIDIA CUDA** acceleration:
1. Ensure the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) is installed on your Linux host.
2. Run with `--gpus all` and set `ORION_HARDWARE_ACCELERATOR=cuda`:

```bash
docker run --gpus all -e ORION_HARDWARE_ACCELERATOR=cuda -p 8000:8000 -p 8080:8080 orion:latest
```

Or in `docker-compose.yml`, add:
```yaml
services:
  orion:
    environment:
      - ORION_HARDWARE_ACCELERATOR=cuda
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

---

## 📁 Persistent Volumes & Data Layout

The container mounts local directories so your data survives container restarts:

| Host Directory | Container Path | Purpose |
|---|---|---|
| `./data` | `/app/data` | SQLite database (`orion.db`) storing protocol decisions and runs. |
| `./logs` | `/app/logs` | Structured JSON and rotating application logs (`orion.log`). |
| `./recordings` | `/app/recordings` | Local MP4 recordings and machine-readable `events.json`. |
| `./configs` | `/app/configs` | Read-only mount of experiment protocols and camera YAMLs. |

---

## 🔧 Environment Configuration

You can customize runtime behavior by creating a `.env` file from the provided `.env.docker` template:

```bash
cp .env.docker .env
```

Key environment variables:
- `ORION_CAMERA_SOURCE`: Path to video file (`assets/sample_replay.mp4`) or RTSP feed URI.
- `ORION_HARDWARE_ACCELERATOR`: `cpu` or `cuda`.
- `ORION_STREAMING_ENABLED`: Set to `true` to host the MJPEG stream on port 8080.
- `ORION_LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, or `ERROR`.
- `ORION_ENV`: `development` or `production`.

---

## ❓ Frequently Asked Questions (FAQ)

### 1. What happens if I don't have a webcam connected?
The container automatically detects this and defaults to `assets/sample_replay.mp4`, which feeds a real recorded BAS experiment through object detection, pose estimation, and the protocol state machine.

### 2. How do I pass a physical USB webcam into the container on Linux?
Add the device flag when running Docker:
```bash
docker run --device=/dev/video0:/dev/video0 -e ORION_CAMERA_SOURCE="0" -p 8000:8000 -p 8080:8080 orion:latest
```
Or in `docker-compose.yml`:
```yaml
devices:
  - "/dev/video0:/dev/video0"
```

### 3. How do I view the desktop PySide6 cockpit?
The desktop cockpit is designed for native host execution (`./launch.sh` or `python run.py`). In containerized, cloud, or headless environments, the built-in HTTP MJPEG live stream at `http://localhost:8080/live` alongside the FastAPI REST/WebSocket endpoints at `http://localhost:8000` provides full visibility of the camera, bounding boxes, skeletal joints, and experiment guidance in any browser.
