#!/usr/bin/env bash
# ==============================================================================
# ORION BAS AI Copilot — Container Entrypoint
# Handles runtime initialization, database readiness, and operational profiles
# ==============================================================================
set -e

# Ensure runtime directories exist
mkdir -p /app/data /app/logs /app/recordings 2>/dev/null || true

cat << "EOF"
  ___  ____  ___ ___  _   _ 
 / _ \|  _ \|_ _/ _ \| \ | |
| | | | |_) || | | | |  \| |
| |_| |  _ < | | |_| | |\  |
 \___/|_| \_\___\___/|_| \_|
 Bharatiya Antariksh Station — AI Copilot Container
EOF

echo "Station ID:     ${ORION_STATION_ID:-BAS-SCIENCE-NODE-01}"
echo "Environment:    ${ORION_ENV:-development}"
echo "Accelerator:    ${ORION_HARDWARE_ACCELERATOR:-cpu}"
echo "Camera Source:  ${ORION_CAMERA_SOURCE:-assets/sample_replay.mp4}"
echo "=================================================================="

# Optional database migration
if [ -f "/app/alembic.ini" ]; then
    echo "Checking persistence schema migrations..."
    alembic upgrade head 2>/dev/null || echo "Alembic auto-migration completed or skipped."
fi

# Route operational commands
case "$1" in
    api|"")
        echo "Starting ORION Headless Perception & API Server on ${ORION_API_HOST:-0.0.0.0}:${ORION_API_PORT:-8000}..."
        exec uvicorn orion.api.app:create_app --factory \
            --host "${ORION_API_HOST:-0.0.0.0}" \
            --port "${ORION_API_PORT:-8000}" \
            --workers "${ORION_API_WORKERS:-1}"
        ;;
    doctor)
        echo "Running ORION System Diagnostic Doctor..."
        exec python scripts/doctor.py
        ;;
    test)
        echo "Running ORION Unit Test Suite..."
        shift
        exec pytest tests/unit "$@"
        ;;
    smoke)
        echo "Running ORION Replay Video Smoke Test..."
        shift
        exec python scripts/smoke_test_replay.py assets/sample_replay.mp4 configs/protocols/bas_e01_a.yaml "${@:-40}"
        ;;
    demo)
        echo "Running ORION Perception Replay Demo..."
        shift
        exec python scripts/smoke_test_replay.py assets/sample_replay.mp4 configs/protocols/bas_e01_a.yaml "${@:-200}"
        ;;
    gui-headless)
        echo "Launching Native Qt Cockpit inside virtual X11 framebuffer (Xvfb)..."
        shift
        exec xvfb-run -a python run.py --demo "$@"
        ;;
    bash|sh)
        exec "$@"
        ;;
    *)
        exec "$@"
        ;;
esac
