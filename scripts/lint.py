"""Linting orchestrator script running Ruff static analysis."""

import subprocess
import sys


def lint() -> int:
    print("🔍 Running Ruff static analysis...")
    result = subprocess.run(["uv", "run", "ruff", "check", "."])
    return result.returncode


if __name__ == "__main__":
    sys.exit(lint())
