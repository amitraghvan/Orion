# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for ORION BAS AI Desktop System.

Produces an air-gapped, native desktop executable bundling all C++ extensions,
pre-trained neural network weights, protocol definitions, and PySide6 Qt assets.
"""

import os
import sys
from pathlib import Path

block_cipher = None

workspace_dir = Path(__file__).resolve().parent

# Collect data files
datas = [
    (str(workspace_dir / "config"), "config"),
    (str(workspace_dir / "configs"), "configs"),
    (str(workspace_dir / "models" / "weights"), "models/weights"),
    (str(workspace_dir / "models" / "bas_experiment"), "models/bas_experiment"),
    (str(workspace_dir / "assets"), "assets"),
]

# Collect binaries (native C++ pybind11 module)
binaries = []
if sys.platform == "darwin":
    so_files = list(workspace_dir.glob("orion_native*.so"))
    for f in so_files:
        binaries.append((str(f), "."))
elif sys.platform == "win32":
    pyd_files = list(workspace_dir.glob("orion_native*.pyd"))
    for f in pyd_files:
        binaries.append((str(f), "."))
elif sys.platform.startswith("linux"):
    so_files = list(workspace_dir.glob("orion_native*.so"))
    for f in so_files:
        binaries.append((str(f), "."))

hiddenimports = [
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "torch",
    "torchvision",
    "cv2",
    "yaml",
    "pydantic",
    "pyttsx3",
    "pyttsx3.drivers",
    "pyttsx3.drivers.nsss",
    "pyttsx3.drivers.sapi5",
    "sqlite3",
]

excludes = [
    "tkinter",
    "matplotlib",
    "IPython",
    "notebook",
    "pytest",
    "uvicorn",
    "fastapi",
]

a = Analysis(
    ["run.py"],
    pathex=[
        str(workspace_dir),
        str(workspace_dir / "ai" / "src"),
        str(workspace_dir / "backend" / "src"),
    ],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ORION",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=os.environ.get("ORION_BUILD_CONSOLE", "0") == "1",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(workspace_dir / "assets" / "icon.ico") if (workspace_dir / "assets" / "icon.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ORION",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="ORION.app",
        icon=None,
        bundle_identifier="in.isro.orion.bas",
        info_plist={
            "NSCameraUsageDescription": "ORION requires camera access for AI Human Activity Recognition in BAS experiments.",
            "NSMicrophoneUsageDescription": "ORION requires microphone access for offline voice assistance.",
            "NSHighResolutionCapable": True,
        },
    )
