#!/usr/bin/env bash
# ==============================================================================
# ORION BAS AI DESKTOP - macOS STANDALONE BUILD SCRIPT
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${WORKSPACE_ROOT}"

echo "============================================================"
echo "  ORION BAS Desktop System - macOS Deployment Packager      "
echo "============================================================"

PYTHON_BIN="${WORKSPACE_ROOT}/.venv/bin/python"
if [ ! -f "${PYTHON_BIN}" ]; then
    PYTHON_BIN="python3"
fi

echo "[1/4] Checking Python environment..."
"${PYTHON_BIN}" --version

echo "[2/4] Verifying C++ native library..."
if [ ! -f "${WORKSPACE_ROOT}/orion_native"*.so ]; then
    echo "Compiling C++20 native engine..."
    cmake -B build -S . -DCMAKE_BUILD_TYPE=Release -DPython_EXECUTABLE="${PYTHON_BIN}"
    cmake --build build --config Release -j
    cp build/orion_native*.so "${WORKSPACE_ROOT}/"
fi
echo "  Native library verified."

echo "[3/4] Running PyInstaller..."
"${PYTHON_BIN}" -m PyInstaller build.spec --noconfirm --clean

echo "[4/4] Validating bundle..."
if [ -d "dist/ORION" ]; then
    echo "  Packaging complete: dist/ORION"
    echo "To run:"
    echo "  ./dist/ORION/ORION"
else
    echo "Error: dist/ORION not found!"
    exit 1
fi
