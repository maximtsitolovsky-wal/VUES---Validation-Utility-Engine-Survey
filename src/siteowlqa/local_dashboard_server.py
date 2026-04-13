"""Tiny localhost server for the generated SiteOwlQA dashboard.

Serves the output/ directory with no-cache headers so the browser always sees
freshly-regenerated HTML instead of stale file snapshots.
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
_PORT = 8765
_HEALTH_PATH = "/executive_dashboard.html"
_STARTUP_WAIT_SECONDS = 5.0


def _server_command(output_dir: Path) -> list[str]:
    return [
        sys.executable,
        str(Path(__file__).resolve().parent / "tools" / "run_dashboard_server.py"),
        str(output_dir),
        str(_PORT),
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


def ensure_dashboard_server(output_dir: Path) -> str:
    """Return the canonical localhost dashboard base URL, starting the server if needed."""
    output_dir = output_dir.resolve()
    base_url = f"http://{_HOST}:{_PORT}"
    health_url = f"{base_url}{_HEALTH_PATH}"

    if _can_connect(_HOST, _PORT) and _healthcheck(health_url):
        return base_url

    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    subprocess.Popen(  # noqa: S603
        _server_command(output_dir),
        cwd=str(output_dir.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
        close_fds=True,
    )

    deadline = time.time() + _STARTUP_WAIT_SECONDS
    while time.time() < deadline:
        if _can_connect(_HOST, _PORT) and _healthcheck(health_url):
            return base_url
        time.sleep(0.2)

    raise RuntimeError(f"Dashboard server did not start on {base_url}")
