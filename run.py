#!/usr/bin/env python3
"""Universal Desktop Launcher for ORION AI BAS Experiment Assistant."""

import sys
from pathlib import Path

# Add workspace root to sys.path
workspace_root = Path(__file__).resolve().parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from app.main import main

if __name__ == "__main__":
    main()
