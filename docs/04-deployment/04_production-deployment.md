# ORION Production Flight Deployment Guide

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments (SIH26174)  
**Organization:** Indian Space Research Organisation (ISRO)  
**Date:** September 17, 2026  
**Status:** PRODUCTION DEPLOYMENT STANDARD  

---

## 1. Spacecraft Flight Deployment Architecture

For deployment aboard space station payload racks or ground control monitoring stations, ORION is configured as an isolated, resilient system with process supervision and disk space safeguards.

```
┌─────────────────────────────────────────────────────────────┐
│                 Systemd Process Supervisor                  │
│                     (orion-copilot.service)                 │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     ORION Core Process                      │
│                  (./launch.sh --camera 0)                   │
├──────────────────────────────┬──────────────────────────────┤
│ 1. Native Qt Cockpit GUI     │ 2. Threaded Capture & AI     │
│ 3. Offline Voice Synthesizer │ 4. Session Video Recorder    │
│ 5. Local SQLite Persistence  │ 6. IP MJPEG Video Streamer   │
└──────────────────────────────┴──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   Storage Watchdog Daemon                   │
│          Enforces 80% disk threshold & log rotation         │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Systemd Service Specification

For Linux-based flight nodes (Ubuntu Core, Debian, or embedded Linux), deploy the following unit file at `/etc/systemd/system/orion-copilot.service`:

```ini
[Unit]
Description=ORION AI BAS Experiment Assistant (SIH26174)
After=network.target sound.target

[Service]
Type=simple
User=astronaut
WorkingDirectory=/opt/orion
ExecStart=/opt/orion/launch.sh
Restart=on-failure
RestartSec=5s
KillMode=process
TimeoutStopSec=10s

# Sandboxing and security
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/opt/orion/recordings /opt/orion/data /opt/orion/logs
NoNewPrivileges=true

# Environment
Environment=PYTHONUNBUFFERED=1
Environment=ORION_STATION_ID=BAS-FLIGHT-01
Environment=ORION_ENV=production

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable orion-copilot.service
sudo systemctl start orion-copilot.service
```

---

## 3. Containerized Air-Gapped Deployment (Docker / Podman)

For isolated containerized flight platforms:

```dockerfile
FROM python:3.11-slim-bookworm

# Install required system runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    espeak-ng \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy offline wheel cache and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose streaming and telemetry ports
EXPOSE 8080 8000

ENTRYPOINT ["./launch.sh"]
```

Run container with camera and audio access:
```bash
docker run -d \
    --name orion-flight \
    --device=/dev/video0:/dev/video0 \
    --device=/dev/snd:/dev/snd \
    -p 8080:8080 \
    -p 8000:8000 \
    -v /var/orion/recordings:/app/recordings \
    -v /var/orion/data:/app/data \
    orion:latest
```

---

## 4. Hardware Watchdogs & Resilience Invariants

1. **Auto-Restart on Exception:** Systemd or container runtime restarts ORION within 5 seconds if a kernel-level hardware crash occurs.
2. **Camera Reconnect:** If USB/CSI camera is temporarily disconnected, `LiveCameraSource` automatically attempts reconnection at 1s, 2s, and 4s intervals without process termination.
3. **Graceful Shutdown:** `SIGINT` or `SIGTERM` triggers `lifecycle.shutdown()`, flushing video frames from memory buffers to disk, finalizing `metadata.json`, and committing SQLite database transactions before exit.
4. **Storage Safeguards:** When disk utilization on `/opt/orion/recordings` exceeds 85%, the storage manager archives or purges older sessions to prevent disk full faults.
