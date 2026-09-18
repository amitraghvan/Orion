FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install OpenCV system libraries, build tools, cmake, FFmpeg, audio, and X11/Qt dependencies
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
    libx11-xcb1 \
    libxcb-xinerama0 \
    libxkbcommon-x11-0 \
    ffmpeg \
    espeak-ng \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 22.x LTS & npm for developer tooling
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && cp /root/.local/bin/uv /usr/local/bin/uv \
    && cp /root/.local/bin/uvx /usr/local/bin/uvx

# Set working directory
WORKDIR /workspace
