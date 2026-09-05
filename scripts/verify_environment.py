"""Strict environment verification script for ORION BAS AI Copilot."""

import shutil
import sys
from pathlib import Path


def verify() -> bool:
    print("==================================================================")
    print("🔍 ORION BAS AI Copilot — Environment Verification")
    print("==================================================================")

    all_passed = True

    # 1. Python Version Check (Mandatory 3.11)
    py_ver = sys.version_info
    print(f"🐍 Python Version: {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    if py_ver.major == 3 and py_ver.minor == 11:
        print("   ✅ Python 3.11 runtime verified.")
    else:
        print(
            f"   ⚠️ WARNING: Expected Python 3.11, detected {py_ver.major}.{py_ver.minor}.{py_ver.micro}"
        )

    # 2. Package Manager uv
    uv_bin = shutil.which("uv")
    if uv_bin:
        print(f"   ✅ 'uv' found: {uv_bin}")
    else:
        print("   ❌ 'uv' not found in PATH")
        all_passed = False

    # 3. Node.js & npm
    node_bin = shutil.which("node")
    npm_bin = shutil.which("npm")
    if node_bin and npm_bin:
        print(f"   ✅ Node.js found: {node_bin}")
        print(f"   ✅ npm found: {npm_bin}")
    else:
        print("   ⚠️ Node.js or npm not detected in current PATH")

    # 4. Mandatory Directory Layout Check
    root = Path(__file__).resolve().parents[1]
    required_dirs = [
        "backend",
        "frontend",
        "ai",
        "datasets",
        "experiments",
        "deployment",
        "infrastructure",
        "docs",
        "configs",
        "tools",
        "scripts",
        "tests",
        "assets",
        ".github",
    ]

    print("\n📁 Checking Monorepo Layout:")
    for d in required_dirs:
        dir_path = root / d
        if dir_path.is_dir():
            print(f"   ✅ {d}/")
        else:
            print(f"   ❌ Missing required directory: {d}/")
            all_passed = False

    # 5. Core Configuration Files Check
    required_files = [
        "pyproject.toml",
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".gitignore",
        ".env.example",
        "configs/base.yaml",
        "experiments/experiment_template.yaml",
    ]

    print("\n📄 Checking Core Specifications:")
    for f in required_files:
        f_path = root / f
        if f_path.is_file():
            print(f"   ✅ {f}")
        else:
            print(f"   ❌ Missing file: {f}")
            all_passed = False

    print("==================================================================")
    if all_passed:
        print("🎉 ENVIRONMENT VERIFICATION PASSED — Ready for Phase 0 execution.")
    else:
        print("❌ ENVIRONMENT VERIFICATION FAILED — Issues detected above.")
    print("==================================================================")

    return all_passed


if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
