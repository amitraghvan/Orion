"""Test orchestrator script running pytest with coverage."""

import subprocess
import sys


def run_tests() -> int:
    print("🧪 Running Pytest test suite...")
    result = subprocess.run(["uv", "run", "pytest", "-v", "tests/"])
    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests())
