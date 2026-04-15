#!/usr/bin/env python3
"""git_autopush.py — Watch the repo for changes and auto-commit + push.

Debounces filesystem events so a flurry of saves results in ONE clean commit,
not 40 noisy ones.  Pushes to every configured remote on the current branch.

Usage:
    python scripts/git_autopush.py                    # default: 10s debounce
    python scripts/git_autopush.py --debounce 5       # commit 5s after last change
    python scripts/git_autopush.py --remotes origin walmart-origin
    python scripts/git_autopush.py --dry-run          # print what would happen, no push
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

_REPO = Path(__file__).resolve().parents[1]

# Directories / patterns that are never interesting to watch.
# Git already respects .gitignore — this is just to avoid noisy re-triggers
# from build artifacts that land on disk mid-operation.
_IGNORE_DIRS = {
    "__pycache__", ".git", "output", "logs", "temp",
    ".venv", "venv", "node_modules", "archive", "share",
    "served_dashboard", "VUES---Validation-Utility-Engine-Survey",
}
_IGNORE_SUFFIXES = {".pyc", ".pyo", ".pyd", ".log", ".tmp", ".sqlite-journal"}


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=str(_REPO), capture_output=True, text=True, check=check,
    )


def _current_branch() -> str:
    r = _run(["git", "branch", "--show-current"])
    return r.stdout.strip() or "main"


def _remotes() -> list[str]:
    r = _run(["git", "remote"])
    return [line.strip() for line in r.stdout.splitlines() if line.strip()]


def _has_changes() -> bool:
    r = _run(["git", "status", "--porcelain"])
    return bool(r.stdout.strip())


def _changed_summary() -> str:
    """Return a compact summary of staged+unstaged changes for the commit msg."""
    r = _run(["git", "status", "--porcelain"])
    lines = r.stdout.strip().splitlines()
    if not lines:
        return "no changes"
    # e.g. "M src/foo.py, ?? bar.py" — cap at 5 files to keep msg readable
    files = [l[3:].strip() for l in lines[:5]]
    suffix = f" (+{len(lines) - 5} more)" if len(lines) > 5 else ""
    return ", ".join(files) + suffix


def _do_commit_and_push(remotes: list[str], branch: str, dry_run: bool) -> None:
    """Stage everything, commit, and push to all remotes. Safe to call if clean."""
    if not _has_changes():
        _log("Nothing to commit — tree is clean, skipping.")
        return

    summary = _changed_summary()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"auto: {stamp} | {summary}"

    _log(f"Staging all changes ...")
    if not dry_run:
        _run(["git", "add", "-A"])

    _log(f"Committing: {msg!r}")
    if not dry_run:
        r = _run(["git", "commit", "-m", msg], check=False)
        if r.returncode != 0:
            _log(f"[WARN] Commit failed: {r.stderr.strip() or r.stdout.strip()}")
            return
        _log(f"Committed OK.")

    for remote in remotes:
        _log(f"Pushing to {remote}/{branch} ...")
        if not dry_run:
            r = _run(["git", "push", remote, branch], check=False)
            if r.returncode == 0:
                _log(f"[OK] Pushed to {remote}/{branch}.")
            else:
                _log(f"[ERROR] Push to {remote} failed:\n{r.stderr.strip() or r.stdout.strip()}")


class _DebounceHandler(FileSystemEventHandler):
    """Coalesces rapid filesystem events into a single commit after a quiet window."""

    def __init__(self, debounce: float, remotes: list[str], branch: str, dry_run: bool) -> None:
        super().__init__()
        self._debounce = debounce
        self._remotes = remotes
        self._branch = branch
        self._dry_run = dry_run
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._pending_paths: set[str] = set()

    def _should_ignore(self, path: str) -> bool:
        p = Path(path)
        if any(part in _IGNORE_DIRS for part in p.parts):
            return True
        if p.suffix in _IGNORE_SUFFIXES:
            return True
        return False

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        src = str(event.src_path)
        if self._should_ignore(src):
            return

        with self._lock:
            self._pending_paths.add(src)
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        with self._lock:
            paths = set(self._pending_paths)
            self._pending_paths.clear()
            self._timer = None

        rel_paths = sorted(
            str(Path(p).relative_to(_REPO)) for p in paths
            if Path(p).is_relative_to(_REPO)
        )
        _log(f"Change detected in: {', '.join(rel_paths[:5])}"
             + (f" (+{len(rel_paths)-5} more)" if len(rel_paths) > 5 else ""))
        _do_commit_and_push(self._remotes, self._branch, self._dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--debounce", type=float, default=10.0,
                        help="Seconds of quiet after last change before committing (default: 10)")
    parser.add_argument("--remotes", nargs="+", default=None,
                        help="Remotes to push to (default: all configured remotes)")
    parser.add_argument("--branch", default=None,
                        help="Branch to push (default: current branch)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen — no actual commit or push")
    args = parser.parse_args()

    branch = args.branch or _current_branch()
    remotes = args.remotes or _remotes()

    if not remotes:
        _log("[ERROR] No git remotes configured. Add one with: git remote add origin <url>")
        sys.exit(1)

    mode = " [DRY RUN]" if args.dry_run else ""
    _log(f"git-autopush starting{mode}")
    _log(f"  Repo:     {_REPO}")
    _log(f"  Branch:   {branch}")
    _log(f"  Remotes:  {', '.join(remotes)}")
    _log(f"  Debounce: {args.debounce}s")
    _log(f"  Watching: {_REPO}")
    _log("  Press Ctrl+C to stop.")

    handler = _DebounceHandler(
        debounce=args.debounce,
        remotes=remotes,
        branch=branch,
        dry_run=args.dry_run,
    )

    observer = Observer()
    observer.schedule(handler, str(_REPO), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _log("Stopping watcher ...")
        observer.stop()

    observer.join()
    _log("git-autopush stopped.")


if __name__ == "__main__":
    main()
