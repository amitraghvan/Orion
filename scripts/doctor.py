"""Comprehensive system health and readiness diagnostic doctor for ORION BAS AI Copilot."""

import platform
import shutil
import sys
from pathlib import Path


def run_doctor() -> int:
    print("==================================================================")
    print("🩺 ORION BAS AI COPILOT — SYSTEM DOCTOR")
    print("==================================================================")

    checks_passed = 0
    total_checks = 7

    # Check 1: Python Version
    py_ver = sys.version_info
    print("\n1. Python Runtime:")
    if py_ver.major == 3 and py_ver.minor == 11:
        print(f"   ✅ Python {py_ver.major}.{py_ver.minor}.{py_ver.micro} (Verified 3.11 target)")
        checks_passed += 1
    else:
        print(f"   ⚠️ Python {py_ver.major}.{py_ver.minor}.{py_ver.micro} (Recommended: 3.11)")

    # Check 2: Package Manager uv
    print("\n2. Package Manager:")
    uv_bin = shutil.which("uv")
    if uv_bin:
        print(f"   ✅ 'uv' installed: {uv_bin}")
        checks_passed += 1
    else:
        print("   ❌ 'uv' not found in PATH")

    # Check 3: Node & npm
    print("\n3. Frontend Environment:")
    node_bin = shutil.which("node")
    npm_bin = shutil.which("npm")
    if node_bin and npm_bin:
        print(f"   ✅ Node.js: {node_bin}")
        print(f"   ✅ npm: {npm_bin}")
        checks_passed += 1
    else:
        print("   ⚠️ Node.js or npm not installed")

    # Check 4: Monorepo Structure
    print("\n4. Monorepo Architecture:")
    root = Path(__file__).resolve().parents[1]
    required_dirs = [
        "backend",
        "app",
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
    ]
    missing = [d for d in required_dirs if not (root / d).is_dir()]
    if not missing:
        print(f"   ✅ All {len(required_dirs)} root subsystem directories present (Native Qt App + Backend)")
        checks_passed += 1
    else:
        print(f"   ❌ Missing directories: {', '.join(missing)}")

    # Check 5: Settings & Config Loading
    print("\n5. Layered Configuration System:")
    try:
        from orion.core.config import get_settings

        settings = get_settings()
        print(
            f"   ✅ Settings loaded successfully: Station '{settings.station_id}', Env '{settings.env}'"
        )
        checks_passed += 1
    except Exception as exc:
        print(f"   ❌ Failed to load settings: {exc}")

    # Check 6: Database Async Engine Factory
    print("\n6. Persistence Layer Engine:")
    try:
        from orion.db.session import get_engine

        engine = get_engine()
        print(f"   ✅ Async database engine created: {engine.url.drivername}")
        checks_passed += 1
    except Exception as exc:
        print(f"   ❌ Failed to initialize database engine: {exc}")

    # Check 7: Hardware & OS Architecture
    print("\n7. Hardware & Host Architecture:")
    os_name = platform.system()
    machine = platform.machine()
    print(f"   ℹ️ OS: {os_name} ({machine})")
    checks_passed += 1

    # Final Score
    readiness_pct = (checks_passed / total_checks) * 100
    print("\n==================================================================")
    print(
        f"📊 DOCTOR READINESS SCORE: {readiness_pct:.1f}% ({checks_passed}/{total_checks} checks passed)"
    )
    if checks_passed >= 6:
        print("🎉 Phase 0 Foundation is nominal and ready for development!")
    else:
        print("⚠️ Subsystems require attention before proceeding.")
    print("==================================================================")

    return 0 if checks_passed >= 6 else 1


if __name__ == "__main__":
    sys.exit(run_doctor())
