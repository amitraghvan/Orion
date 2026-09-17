#!/usr/bin/env bash
# Quick launcher for ORION Desktop Application
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"
exec "${SCRIPT_DIR}/.venv/bin/python" "${SCRIPT_DIR}/run.py" "$@"
