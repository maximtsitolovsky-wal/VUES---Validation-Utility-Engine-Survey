"""Serve a dashboard output directory over localhost with aggressive no-cache headers.

Also exposes tiny localhost-only control endpoints so the dashboard can start,
stop, and inspect the SiteOwlQA background process without depending on an
external launcher after first use.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

_WORKDIR = Path(__file__).resolve().parents[1]
_START_SCRIPT = _WORKDIR / "ops" / "windows" / "start_siteowlqa_background.ps1"
_STOP_SCRIPT = _WORKDIR / "ops" / "windows" / "stop_siteowlqa_background.ps1"
# Prefer project venv; fall back to the interpreter running this very server
_VENV_PYTHON = _WORKDIR / ".venv" / "Scripts" / "python.exe"
_PYTHON = _VENV_PYTHON if _VENV_PYTHON.exists() else Path(sys.executable)
_MAIN_SCRIPT = _WORKDIR / "main.py"
_OUTPUT_DIR = _WORKDIR / "output"
_REALTIME_SNAPSHOT = _OUTPUT_DIR / "realtime_snapshot.json"
_REBUILD_SCRIPT = _WORKDIR / "tools" / "rebuild_current_dashboard.py"
_STALE_AFTER_MINUTES = 15
_rebuild_lock = threading.Lock()
_rebuild_in_progress = False


class NoCacheDashboardHandler(SimpleHTTPRequestHandler):
    """Static-file handler tuned for regenerated dashboards."""

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _request_path(self) -> str:
        return urlsplit(self.path).path.rstrip('/') or '/'

    def do_GET(self) -> None:  # noqa: N802
        path = self._request_path()
        if path == "/api/app/status":
            self._write_json(HTTPStatus.OK, _app_status_payload())
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = self._request_path()
        if path == "/api/app/start":
            self._write_json(HTTPStatus.ACCEPTED, _launch_powershell_script(_START_SCRIPT, action="start"))
            return
        if path == "/api/app/stop":
            self._write_json(HTTPStatus.ACCEPTED, _launch_powershell_script(_STOP_SCRIPT, action="stop"))
            return
        if path == "/api/app/rebuild":
            self._write_json(HTTPStatus.ACCEPTED, _request_dashboard_rebuild(reason="manual"))
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found", "path": path})

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("port", type=int)
    return parser.parse_args()


def _is_app_running() -> bool:
    # Use the actual resolved path so this works on any machine / clone location.
    main_path = str(_MAIN_SCRIPT).replace("\\", "\\\\")
    cmd = (
        "Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -match '^python(\\.exe)?$' -and ("
        f"$_.CommandLine -like '*{main_path}*' -or "
        "$_.CommandLine -match '(^|\\s)main\\.py(\\s|$)'"
        ") } | Select-Object -First 1 | ForEach-Object { 'RUNNING' }"
    )
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            cmd,
        ],
        cwd=_WORKDIR,
        capture_output=True,
        text=True,
        check=False,
    )
    return "RUNNING" in (result.stdout or "")


def _launch_powershell_script(script_path: Path, *, action: str) -> dict[str, Any]:
    if not script_path.exists():
        return {"ok": False, "error": f"Script not found: {script_path}", "running": _is_app_running()}

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    subprocess.Popen(  # noqa: S603
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
        ],
        cwd=_WORKDIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
        close_fds=True,
    )

    if action == "start":
        _trigger_dashboard_rebuild_background()

    return {
        "ok": True,
        "result": f"{action} requested",
        **_app_status_payload(),
    }


def _trigger_dashboard_rebuild_background() -> bool:
    global _rebuild_in_progress  # noqa: PLW0603
    if not _PYTHON.exists() or not _REBUILD_SCRIPT.exists():
        return False

    with _rebuild_lock:
        if _rebuild_in_progress:
            return False
        _rebuild_in_progress = True

    def _run() -> None:
        global _rebuild_in_progress  # noqa: PLW0603
        try:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            subprocess.run(  # noqa: S603
                [str(_PYTHON), str(_REBUILD_SCRIPT)],
                cwd=_WORKDIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
                close_fds=True,
                check=False,
            )
        finally:
            with _rebuild_lock:
                _rebuild_in_progress = False

    threading.Thread(target=_run, name="dashboard-rebuild", daemon=True).start()
    return True


def _load_realtime_snapshot() -> dict[str, Any] | None:
    if not _REALTIME_SNAPSHOT.exists():
        return None
    try:
        return json.loads(_REALTIME_SNAPSHOT.read_text(encoding="utf-8"))
    except Exception:
        return None


def _snapshot_age_minutes(snapshot: dict[str, Any] | None) -> int | None:
    if not snapshot:
        return None
    ts = snapshot.get("generated_at_utc")
    if not ts:
        return None
    try:
        generated = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    age_seconds = max(0.0, (now - generated).total_seconds())
    return int(round(age_seconds / 60.0))


def _request_dashboard_rebuild(*, reason: str) -> dict[str, Any]:
    started = _trigger_dashboard_rebuild_background()
    return {
        "ok": True,
        "result": "rebuild started" if started else "rebuild already in progress",
        "reason": reason,
        **_app_status_payload(),
    }


def _app_status_payload() -> dict[str, Any]:
    snapshot = _load_realtime_snapshot()
    snapshot_age = _snapshot_age_minutes(snapshot)
    running = _is_app_running()

    if running and snapshot_age is not None and snapshot_age >= _STALE_AFTER_MINUTES:
        _trigger_dashboard_rebuild_background()

    return {
        "ok": True,
        "running": running,
        "python_exists": _PYTHON.exists(),
        "main_exists": _MAIN_SCRIPT.exists(),
        "start_script_exists": _START_SCRIPT.exists(),
        "stop_script_exists": _STOP_SCRIPT.exists(),
        "rebuild_script_exists": _REBUILD_SCRIPT.exists(),
        "rebuild_in_progress": _rebuild_in_progress,
        "snapshot": snapshot,
        "snapshot_age_minutes": snapshot_age,
        "stale_after_minutes": _STALE_AFTER_MINUTES,
    }


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    if not output_dir.exists() or not output_dir.is_dir():
        raise SystemExit(f"Output directory does not exist: {output_dir}")

    handler = partial(NoCacheDashboardHandler, directory=os.fspath(output_dir))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
