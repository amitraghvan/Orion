"""Formatting orchestrator script using Ruff format."""

import subprocess
import sys


def format_code() -> int:
    print("🎨 Formatting Python code with Ruff...")
    result = subprocess.run(["uv", "run", "ruff", "format", "."])
    return result.returncode


if __name__ == "__main__":
    sys.exit(format_code())
