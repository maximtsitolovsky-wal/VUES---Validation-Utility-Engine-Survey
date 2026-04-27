#!/usr/bin/env python3
"""dev.py - Local hot-reload launcher for VUES.

Mirrors the Docker Compose Watch + watchmedo setup, but runs natively on
Windows.  When any .py file in src/, tools/, or prompts/ changes, the
running pipeline is killed and restarted automatically.

Usage:
    python dev.py              # default: watches src/, tools/, prompts/
    python dev.py --no-git     # skip launching git-autopush alongside

Under the hood this is just a thin wrapper around 'watchmedo auto-restart'
(from the watchdog package, already in requirements.txt).

Hot-reload matrix (local):
    src/**/*.py       -> auto-restart main.py
    tools/**/*.py     -> auto-restart main.py
    prompts/**        -> auto-restart main.py
    .env / main.py    -> auto-restart main.py  (watchmedo watches main.py dir)
    ui/**             -> dashboard server serves with no-cache + live-reload
    pyproject.toml    -> you need to re-install deps manually

For Docker development, use:  docker compose watch
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_VENV_PYTHON = _ROOT / ".venv" / "Scripts" / "python.exe"
_PYTHON = str(_VENV_PYTHON if _VENV_PYTHON.exists() else Path(sys.executable))
_WATCHMEDO = _ROOT / ".venv" / "Scripts" / "watchmedo.exe"

_BANNER = """
 +===============================================+
 |  VUES -- Hot-Reload Development Mode          |
 |  Watching: src/  tools/  prompts/             |
 |  Auto-restart on any .py / prompt change      |
 |  Dashboard: live-reload enabled (auto F5)     |
 |  Press Ctrl+C to stop                         |
 +===============================================+
"""


def _resolve_watchmedo() -> str:
    """Find the watchmedo executable -- venv first, then PATH."""
    if _WATCHMEDO.exists():
        return str(_WATCHMEDO)
    # Fall back to running it as a Python module
    return f"{_PYTHON} -m watchdog.watchmedo"


def _build_watchmedo_cmd() -> list[str]:
    """Build the watchmedo auto-restart command, mirroring Docker's approach."""
    watchmedo = _resolve_watchmedo()

    # If watchmedo is a path to an exe, use it directly.
    # If it's a "python -m ..." string, split it.
    if os.path.isfile(watchmedo):
        cmd = [watchmedo]
    else:
        cmd = watchmedo.split()

    cmd.extend([
        "auto-restart",
        "--directory", str(_ROOT / "src"),
        "--directory", str(_ROOT / "tools"),
        "--directory", str(_ROOT / "prompts"),
        "--pattern", "*.py;*.txt;*.md",
        "--ignore-pattern", "*/__pycache__/*;*.pyc;*.pyo;*.pyd;*.log",
        "--recursive",
        "--debounce-interval", "1.5",
        "--kill-after", "5",
        "--",
        _PYTHON, str(_ROOT / "main.py"),
    ])
    return cmd


def _launch_git_autopush() -> subprocess.Popen | None:
    """Start git_autopush.py in the background if it exists."""
    script = _ROOT / "scripts" / "git_autopush.py"
    if not script.exists():
        return None

    print("  [DEV] Starting git-autopush in background ...", flush=True)
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    return subprocess.Popen(
        [_PYTHON, str(script)],
        cwd=str(_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="Don't launch git-autopush alongside",
    )
    args = parser.parse_args()

    # Enable live-reload in the dashboard server via environment variable.
    # The server checks this to inject the auto-refresh JS snippet.
    os.environ["VUES_LIVE_RELOAD"] = "1"

    print(_BANNER, flush=True)

    git_proc = None
    if not args.no_git:
        git_proc = _launch_git_autopush()

    cmd = _build_watchmedo_cmd()
    print(f"  [DEV] {' '.join(cmd[:4])} ... (watching for changes)\n", flush=True)

    try:
        proc = subprocess.run(cmd, cwd=str(_ROOT))
        sys.exit(proc.returncode)
    except KeyboardInterrupt:
        print("\n  [DEV] Shutting down hot-reload ...", flush=True)
    finally:
        if git_proc and git_proc.poll() is None:
            print("  [DEV] Stopping git-autopush ...", flush=True)
            git_proc.terminate()
            try:
                git_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                git_proc.kill()
        print("  [DEV] Goodbye!", flush=True)


if __name__ == "__main__":
    main()
