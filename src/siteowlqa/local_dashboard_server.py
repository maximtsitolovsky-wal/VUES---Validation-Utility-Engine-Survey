"""Tiny localhost server for the generated SiteOwlQA dashboard.

Serves the output/ directory with no-cache headers so the browser always sees
freshly-regenerated HTML instead of stale file snapshots.

Port selection: tries _PREFERRED_PORT (8765) first.  If that port is taken by
anything else, the OS assigns any free port.  The chosen port is written to
output/dashboard.port so launchers and scripts can always read the real URL
without hardcoding anything.
"""

from __future__ import annotations

import contextlib
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

_HOST = "127.0.0.1"
_PREFERRED_PORT = 8765
_PORT_FILE_NAME = "dashboard.port"
_HEALTH_PATH = "/index.html"
_STARTUP_WAIT_SECONDS = 8.0


# ---------------------------------------------------------------------------
# Port helpers
# ---------------------------------------------------------------------------

def _find_free_port(preferred: int) -> int:
    """Return preferred port if free, else ask the OS for any free port."""
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.settimeout(0.3)
        if s.connect_ex((_HOST, preferred)) != 0:
            return preferred  # nothing listening there → it's free
    # preferred is taken — let the OS pick one
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _write_port_file(output_dir: Path, port: int) -> None:
    """Persist the active port so launchers can read it."""
    try:
        (output_dir / _PORT_FILE_NAME).write_text(str(port), encoding="utf-8")
    except OSError:
        pass


def read_dashboard_port(output_dir: Path) -> int | None:
    """Read the port the server is currently running on.

    Returns None if the port file is missing or unreadable.
    """
    p = output_dir / _PORT_FILE_NAME
    try:
        return int(p.read_text(encoding="utf-8-sig").strip()) if p.exists() else None
    except (ValueError, OSError):
        return None


def get_dashboard_url(output_dir: Path) -> str:
    """Return the full dashboard URL using the port file, falling back to the preferred port."""
    port = read_dashboard_port(Path(output_dir)) or _PREFERRED_PORT
    return f"http://{_HOST}:{port}/index.html"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _server_command(output_dir: Path, port: int) -> list[str]:
    # run_dashboard_server.py lives at project_root/tools/ (two levels up from this file)
    server_script = Path(__file__).resolve().parents[2] / "tools" / "run_dashboard_server.py"
    return [
        sys.executable,
        str(server_script),
        str(output_dir),
        str(port),
    ]


def _can_connect(host: str, port: int) -> bool:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def _healthcheck(url: str) -> bool:
    try:
        with urlopen(url, timeout=1.5) as resp:  # noqa: S310 - localhost only
            return 200 <= getattr(resp, "status", 500) < 400
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ensure_dashboard_server(output_dir: Path) -> str:
    """Return the localhost dashboard base URL, starting the server if needed.

    Always uses a free port — tries 8765 first, falls back to any OS port.
    Writes the chosen port to output/dashboard.port so every script can
    discover the real URL without hardcoding anything.
    """
    output_dir = output_dir.resolve()

    # 1. Check if a previously-started server is still healthy (port file exists).
    existing_port = read_dashboard_port(output_dir)
    if existing_port is not None:
        base_url = f"http://{_HOST}:{existing_port}"
        health_url = f"{base_url}{_HEALTH_PATH}"
        if _can_connect(_HOST, existing_port) and _healthcheck(health_url):
            return base_url  # already up on the right port

    # 2. Find a free port and start a fresh server process.
    port = _find_free_port(_PREFERRED_PORT)
    _write_port_file(output_dir, port)
    base_url = f"http://{_HOST}:{port}"
    health_url = f"{base_url}{_HEALTH_PATH}"

    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    subprocess.Popen(  # noqa: S603
        _server_command(output_dir, port),
        cwd=str(output_dir.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
        close_fds=True,
    )

    deadline = time.time() + _STARTUP_WAIT_SECONDS
    while time.time() < deadline:
        if _can_connect(_HOST, port) and _healthcheck(health_url):
            return base_url
        time.sleep(0.2)

    raise RuntimeError(
        f"Dashboard server did not start on {base_url} — "
        "check that run_dashboard_server.py is present in tools/ at the project root"
    )
