"""Cross-platform environment bootstrap utility for ORION BAS AI Copilot."""

import shutil
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list[str]) -> None:
    print(f"⚙️ Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"❌ Command failed with return code {result.returncode}")
        sys.exit(result.returncode)


def main() -> None:
    root_dir = Path(__file__).resolve().parents[1]
    print(f"🚀 Bootstrapping ORION repository at: {root_dir}")

    # Copy .env.development to .env if not exists
    env_file = root_dir / ".env"
    env_dev = root_dir / ".env.development"
    if not env_file.exists() and env_dev.exists():
        print("📄 Initializing .env from .env.development...")
        shutil.copy(env_dev, env_file)

    # Check uv
    uv_path = shutil.which("uv")
    if not uv_path:
        print("❌ 'uv' is not installed. Please install uv (https://astral.sh/uv)")
        sys.exit(1)

    print(f"✅ Found uv at {uv_path}")

    # Ensure venv
    venv_dir = root_dir / ".venv"
    if not venv_dir.exists():
        print("📦 Creating virtual environment with Python 3.11...")
        run_cmd(["uv", "venv", "--python", "3.11", str(venv_dir)])

    # Install Python editable package
    print("📦 Installing Python dependencies...")
    run_cmd(["uv", "pip", "install", "-e", f"{root_dir}[dev,test]"])

    print("🎉 Bootstrap successful!")


if __name__ == "__main__":
    main()
