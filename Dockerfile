# ==============================================================================
# Multi-Stage Production & Development Dockerfile for ORION BAS AI Copilot
# Target: Python 3.11 (Bullseye Slim) | Aerospace-Hardened Non-Root Execution
# Exposes: 8000 (FastAPI & Telemetry WS), 8080 (MJPEG Stream), 9090 (Prometheus)
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Dependency Resolution & Native Extension Builder
# ------------------------------------------------------------------------------
FROM python:3.11-slim-bullseye AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install core build toolchain and system library headers
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    cmake \
    pkg-config \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager for fast, deterministic dependency resolution
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && cp /root/.local/bin/uv /usr/local/bin/uv

# Create dedicated virtual environment
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy specifications and source trees needed for installation
COPY pyproject.toml README.md requirements.txt ./
COPY cpp/ cpp/
COPY backend/ backend/
COPY ai/ ai/
COPY datasets/ datasets/
COPY experiments/ experiments/
COPY app/ app/

# Install dependencies (core, scientific, observability, and dev tools)
RUN uv pip install --no-cache -r requirements.txt \
    && uv pip install --no-cache -e ".[all]" \
    && uv pip install --no-cache pybind11

# Attempt C++ native module build (graceful fallback if compilation fails)
RUN if [ -f "cpp/CMakeLists.txt" ]; then \
        mkdir -p cpp_build && \
        cd cpp_build && \
        cmake ../cpp -DPython_EXECUTABLE=/opt/venv/bin/python && \
        cmake --build . --parallel $(nproc) && \
        cp orion_native*.so /opt/venv/lib/python3.11/site-packages/ 2>/dev/null || true && \
        cd .. && rm -rf cpp_build; \
    fi

# ------------------------------------------------------------------------------
# Stage 2: Final Runtime Image
# ------------------------------------------------------------------------------
FROM python:3.11-slim-bullseye AS runner

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    ORION_ENV=development \
    ORION_API_HOST=0.0.0.0 \
    ORION_API_PORT=8000 \
    ORION_STREAMING_PORT=8080 \
    ORION_CAMERA_SOURCE=assets/sample_replay.mp4 \
    ORION_HARDWARE_ACCELERATOR=cpu \
    ORION_DATABASE_URL=sqlite+aiosqlite:////app/data/orion.db \
    ORION_LOG_FILE=/app/logs/orion.log \
    PYTHONPATH=/app

# Install minimal runtime libraries for OpenCV, audio alerts, and virtual display
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
    espeak-ng \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Create isolated non-root user (orion:1001) for aerospace container security
RUN groupadd -g 1001 orion && \
    useradd -u 1001 -g orion -m -s /bin/bash orion

WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application assets, configurations, code, and pretrained models
COPY configs/ /app/configs/
COPY backend/ /app/backend/
COPY ai/ /app/ai/
COPY app/ /app/app/
COPY datasets/ /app/datasets/
COPY experiments/ /app/experiments/
COPY models/ /app/models/
COPY assets/ /app/assets/
COPY scripts/ /app/scripts/
COPY tests/ /app/tests/
COPY pyproject.toml README.md run.py alembic.ini ./

# Copy and configure entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create persistent storage directories with proper permissions
RUN mkdir -p /app/data /app/logs /app/recordings && \
    chown -R orion:orion /app

# Switch to non-root user
USER orion

# Expose primary communication ports:
# 8000: REST API & Telemetry WebSocket
# 8080: Multipart MJPEG Live Stream
# 9090: Prometheus Metrics
EXPOSE 8000 8080 9090

# Container Healthcheck (polls active live health endpoint)
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://127.0.0.1:8000/api/v1/health/live || exit 1

# Default Entrypoint and execution command
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["api"]
