"""
scout_sync_worker.py — Downloads Scout Airtable images as part of the pipeline.

Runs as a daemon thread inside the main SiteOwlQA process.
On startup: syncs immediately (60s delay so the pipeline warms up first).
Then: re-syncs every SYNC_INTERVAL_HOURS so images stay current.

Network note (settled 2026-04-15, MEMORY.md):
  Python requests CANNOT reach v5.airtableusercontent.com on Walmart
  network — DNS blocked at WinSock level.  PowerShell Invoke-WebRequest
  (WinINet / browser stack) CAN reach it via PAC/auto-proxy.
  API record fetching uses requests.  Image downloads use PowerShell subprocess.

Output layout:
  OUT_ROOT/<Site Number>/site_info.json   ← survey field data
  OUT_ROOT/<Site Number>/<filename>.jpg   ← images, flat, no subfolders
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

import requests

log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
_API_KEY   = os.getenv("SCOUT_AIRTABLE_API_KEY", "")
_BASE_ID   = os.getenv("SCOUT_AIRTABLE_BASE_ID", "appAwgaX89x0JxG3Z")
_TABLE_ID  = os.getenv("SCOUT_AIRTABLE_TABLE_ID", "tblC4o9AvVulyxFMk")
_IMAGE_COL = "Upload Images"
_SITE_COL  = "Site Number"

_OUT_ROOT = Path(
    r"C:\Users\vn59j7j\OneDrive - Walmart Inc"
    r"\Documents\BaselinePrinter\Scout Files"
)

_AIRTABLE_URL = f"https://api.airtable.com/v0/{_BASE_ID}/{_TABLE_ID}"
_AIRTABLE_HDR = {"Authorization": f"Bearer {_API_KEY}"}

STARTUP_DELAY_SECONDS = 60          # wait for pipeline to warm up first
SYNC_INTERVAL_HOURS   = 6          # re-sync every 6 hours while running


# ── Helpers ───────────────────────────────────────────────────────────────────
def _sanitize(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", str(name)).strip()


def _fetch_records() -> list[dict]:
    records, params = [], {}
    while True:
        resp = requests.get(
            _AIRTABLE_URL, headers=_AIRTABLE_HDR, params=params, timeout=30
        )
        resp.raise_for_status()
        body = resp.json()
        records.extend(body.get("records", []))
        offset = body.get("offset")
        if not offset:
            break
        params = {"offset": offset}
        time.sleep(0.2)
    return records


def _ps_download(url: str, dest: Path, retries: int = 2) -> bool:
    """Download via PowerShell Invoke-WebRequest (WinINet/browser stack)."""
    cmd = (
        f"Invoke-WebRequest -Uri '{url}' -OutFile '{dest}' "
        f"-UseBasicParsing -TimeoutSec 30"
    )
    for attempt in range(1, retries + 1):
        try:
            result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True, text=True, timeout=45,
            )
            if result.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
                return True
            err = (result.stderr or result.stdout or "unknown").strip()[:120]
            log.warning("Scout download attempt %d/%d failed: %s", attempt, retries, err)
        except subprocess.TimeoutExpired:
            log.warning("Scout download attempt %d/%d timed out", attempt, retries)
        if attempt < retries:
            time.sleep(2)
    return False


def _save_site_info(site_dir: Path, record: dict) -> None:
    info_path = site_dir / "site_info.json"
    existing: list = []
    if info_path.exists():
        try:
            data = json.loads(info_path.read_text(encoding="utf-8"))
            existing = data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            pass
    existing.append({
        "airtable_id": record["id"],
        "created":     record["createdTime"],
        "fields":      record.get("fields", {}),
    })
    info_path.write_text(
        json.dumps(existing, indent=2, default=str), encoding="utf-8"
    )


def _run_sync() -> tuple[int, int, int]:
    """Fetch all Scout records and download any missing images.

    Returns (ok, skip, err) counts.
    """
    _OUT_ROOT.mkdir(parents=True, exist_ok=True)

    records = _fetch_records()
    log.info("ScoutSync: fetched %d record(s) from Scout Airtable.", len(records))

    ok = err = skip = 0

    for rec in records:
        fields      = rec.get("fields", {})
        site        = _sanitize(str(fields.get(_SITE_COL, f"UNKNOWN_{rec['id']}")))
        attachments = fields.get(_IMAGE_COL) or []

        if not attachments:
            continue

        site_dir = _OUT_ROOT / site
        site_dir.mkdir(parents=True, exist_ok=True)
        _save_site_info(site_dir, rec)

        for att in attachments:
            filename = _sanitize(att.get("filename") or att.get("id", "file"))
            dest     = site_dir / filename
            if dest.exists() and dest.stat().st_size > 0:
                skip += 1
                continue
            if _ps_download(att["url"], dest):
                log.info("ScoutSync: [OK] %s/%s (%s bytes)", site, filename, f"{dest.stat().st_size:,}")
                ok += 1
            else:
                log.warning("ScoutSync: [ERR] %s/%s — download failed", site, filename)
                err += 1

    return ok, skip, err


# ── Worker thread ─────────────────────────────────────────────────────────────
class ScoutSyncWorker(threading.Thread):
    """Daemon thread that keeps Scout images synced to local disk.

    Lifecycle mirrors CorrectionWorker:
      - start() called in run_forever() alongside other workers
      - request_shutdown() + join() called in Ctrl-C handler
    """

    def __init__(self) -> None:
        super().__init__(daemon=True, name="scout-sync")
        self._stop = threading.Event()

    def request_shutdown(self) -> None:
        log.info("ScoutSyncWorker: shutdown requested.")
        self._stop.set()

    def run(self) -> None:
        log.info(
            "ScoutSyncWorker started. Initial delay %ds, then every %dh.",
            STARTUP_DELAY_SECONDS,
            SYNC_INTERVAL_HOURS,
        )

        # Wait for the pipeline to warm up before hammering the network
        if self._stop.wait(STARTUP_DELAY_SECONDS):
            return  # shutdown before first run — exit cleanly

        while True:
            log.info("ScoutSyncWorker: starting sync at %s", datetime.now().isoformat())
            try:
                ok, skip, err = _run_sync()
                log.info(
                    "ScoutSyncWorker: sync complete — OK=%d SKIP=%d ERR=%d",
                    ok, skip, err,
                )
            except Exception as exc:  # noqa: BLE001
                log.exception("ScoutSyncWorker: sync failed (non-fatal): %s", exc)

            if self._stop.wait(SYNC_INTERVAL_HOURS * 3600):
                break  # shutdown event fired during sleep

        log.info("ScoutSyncWorker: stopped cleanly.")
