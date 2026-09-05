#!/usr/bin/env bash
# ==============================================================================
# ORION BAS AI Copilot — Environment Setup (POSIX)
# ==============================================================================
set -euo pipefail

echo "=================================================================="
echo "🚀 ORION BAS AI Copilot — Environment Setup"
echo "=================================================================="

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "❌ 'uv' is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "✅ Package manager 'uv' found: $(uv --version)"

# Create virtualenv targeting Python 3.11
echo "📦 Setting up Python 3.11 virtual environment..."
uv venv --python 3.11 .venv
source .venv/bin/activate

# Install Python packages
echo "📦 Installing Python dependencies..."
uv pip install -e ".[all]"

# Install Frontend dependencies if node is present
if command -v npm &> /dev/null; then
    echo "📦 Installing frontend dependencies..."
    npm install --prefix frontend
else
    echo "⚠️ Node.js / npm not found. Skipping frontend dependencies."
fi

# Run doctor diagnostic
echo "🩺 Running system doctor diagnostic..."
python scripts/doctor.py

echo "=================================================================="
echo "🎉 Setup complete! Activate environment with: source .venv/bin/activate"
echo "=================================================================="
