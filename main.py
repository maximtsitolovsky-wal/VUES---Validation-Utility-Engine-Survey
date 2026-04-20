#!/usr/bin/env python3
"""Root entry point wrapper for VUES.

This file provides backward compatibility for users expecting to run:
    python main.py

It ensures the siteowlqa package is findable regardless of how Python was
invoked (system Python, venv, Task Scheduler, .exe wrapper, etc.) by
inserting the src/ directory onto sys.path before any siteowlqa imports.
"""

import sys
from pathlib import Path

# Ensure src/ is on the path so 'siteowlqa' is importable regardless of
# whether this is run via venv, system Python, Task Scheduler, or a .exe.
_SRC_DIR = Path(__file__).parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from siteowlqa.main import run_forever

if __name__ == "__main__":
    run_forever()
