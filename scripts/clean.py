"""Clean build artifacts, python bytecode, caches, and ephemeral logs."""

import shutil
from pathlib import Path


def clean() -> None:
    root = Path(__file__).resolve().parents[1]
    print(f"🧹 Cleaning repository artifacts at: {root}")

    patterns = [
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
        "**/*.pyd",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".coverage",
        "htmlcov",
        "dist",
        "build",
        "*.egg-info",
    ]

    for pattern in patterns:
        for p in root.glob(pattern):
            if p.is_dir():
                print(f"   Deleting directory: {p.relative_to(root)}")
                shutil.rmtree(p, ignore_errors=True)
            elif p.is_file():
                print(f"   Deleting file: {p.relative_to(root)}")
                p.unlink(missing_ok=True)

    print("✨ Clean complete!")


if __name__ == "__main__":
    clean()
