"""download_all_attachments.py — RISK-003 Mitigation.

Fetches ALL Airtable submission records and downloads their attachments
to a permanent local folder labelled with the Site ID.  This prevents
data loss when Airtable CDN URLs expire.

Destination:
  C:\\Users\\vn59j7j\\OneDrive - Walmart Inc\\Documents\\BaselinePrinter
  \\VUE Submissions\\ATTACHMENTS

Naming convention:
  SITE_{site_number}__{submission_id}__{original_filename}
  e.g. SITE_4873__rec8xKmQzT3AbCd__Camera_Survey_4873.xlsx

  When a record has multiple attachments, an index prefix is added:
  SITE_{site_number}__{submission_id}__01__{filename}

Script is fully idempotent: existing files are never overwritten.

Usage:
    # Dry-run — show what WOULD be downloaded, touch nothing
    python scripts/download_all_attachments.py --dry-run

    # Real run — download everything not yet on disk
    python scripts/download_all_attachments.py
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from siteowlqa.airtable_client import _download_via_powershell, _api_request
from siteowlqa.config import ATAIRTABLE_FIELDS as FIELDS, load_config
from siteowlqa.utils import sanitise_filename

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEST_DIR = Path(
    r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Documents"
    r"\BaselinePrinter\VUE Submissions\ATTACHMENTS"
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AttachmentJob:
    record_id: str
    submission_id: str
    site_number: str
    url: str
    original_filename: str
    dest_path: Path


@dataclass
class RunSummary:
    downloaded: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _build_dest_filename(
    site_number: str,
    submission_id: str,
    original_filename: str,
    attachment_index: int,
    attachment_count: int,
) -> str:
    """Compose a safe, human-readable filename for one attachment."""
    safe_site = sanitise_filename(site_number) or "UNKNOWN_SITE"
    safe_sub = sanitise_filename(submission_id) or "UNKNOWN_SUB"
    safe_file = sanitise_filename(original_filename) or "attachment"

    if attachment_count > 1:
        return f"SITE_{safe_site}__{safe_sub}__{attachment_index:02d}__{safe_file}"
    return f"SITE_{safe_site}__{safe_sub}__{safe_file}"


def _collect_jobs(raw_records: list[dict[str, Any]], dest_dir: Path) -> list[AttachmentJob]:
    """Convert raw Airtable record dicts into AttachmentJob list."""
    jobs: list[AttachmentJob] = []

    for raw in raw_records:
        record_id: str = raw["id"]
        f: dict[str, Any] = raw.get("fields", {})

        attachments = f.get(FIELDS.attachment, [])
        if not attachments:
            continue  # no attachment on this record — that's fine

        site_number = str(f.get(FIELDS.site_number, "")).strip() or "UNKNOWN_SITE"
        submission_id = str(f.get(FIELDS.submission_id, record_id)).strip() or record_id
        count = len(attachments)

        for idx, att in enumerate(attachments, start=1):
            url = str(att.get("url", "")).strip()
            filename = str(att.get("filename", "attachment.xlsx")).strip()
            if not url:
                log.warning("Record %s attachment #%d has no URL — skipping.", record_id, idx)
                continue

            dest_filename = _build_dest_filename(
                site_number=site_number,
                submission_id=submission_id,
                original_filename=filename,
                attachment_index=idx,
                attachment_count=count,
            )
            jobs.append(
                AttachmentJob(
                    record_id=record_id,
                    submission_id=submission_id,
                    site_number=site_number,
                    url=url,
                    original_filename=filename,
                    dest_path=dest_dir / dest_filename,
                )
            )

    return jobs


def _fetch_all_raw(cfg) -> list[dict[str, Any]]:
    """Pull every record from Airtable as raw dicts (no status filter)."""
    import requests  # stdlib-ish; already a dependency

    base_url = (
        f"https://api.airtable.com/v0/{cfg.airtable_base_id}/"
        f"{requests.utils.quote(cfg.airtable_table_name, safe='')}"
    )
    headers = {
        "Authorization": f"Bearer {cfg.airtable_token}",
        "Content-Type": "application/json",
    }
    params: dict[str, Any] = {"pageSize": 100}
    raw: list[dict[str, Any]] = []

    while True:
        resp = _api_request("GET", base_url, headers, params=params, timeout=30)
        data = resp.json()
        raw.extend(data.get("records", []))
        log.info("  … fetched %d records so far", len(raw))
        offset = data.get("offset")
        if not offset:
            break
        params["offset"] = offset

    log.info("Total records fetched from Airtable: %d", len(raw))
    return raw


def _run(dry_run: bool) -> RunSummary:
    summary = RunSummary()
    cfg = load_config()

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Destination: %s", DEST_DIR)
    log.info("Mode: %s", "DRY-RUN (no files will be written)" if dry_run else "LIVE")

    log.info("Fetching all records from Airtable …")
    raw_records = _fetch_all_raw(cfg)

    jobs = _collect_jobs(raw_records, DEST_DIR)
    log.info("Attachments found: %d", len(jobs))

    for job in jobs:
        if job.dest_path.exists():
            log.info(
                "SKIP  [%s] %s — already on disk",
                job.site_number, job.dest_path.name,
            )
            summary.skipped += 1
            continue

        if dry_run:
            log.info(
                "WOULD_DL  [%s] %s -> %s",
                job.site_number, job.original_filename, job.dest_path.name,
            )
            summary.downloaded += 1  # counts as "would download" in dry-run
            continue

        try:
            log.info(
                "DOWNLOAD  [%s] %s -> %s",
                job.site_number, job.original_filename, job.dest_path.name,
            )
            _download_via_powershell(job.url, job.dest_path)
            size_kb = job.dest_path.stat().st_size / 1024
            log.info("  ✓ %.1f KB saved", size_kb)
            summary.downloaded += 1
            time.sleep(0.2)  # be polite to Airtable CDN
        except Exception as exc:  # noqa: BLE001
            msg = f"[{job.site_number}] {job.original_filename}: {exc}"
            log.error("  ✗ FAILED — %s", msg)
            summary.failed += 1
            summary.errors.append(msg)

    return summary


def _print_summary(summary: RunSummary, dry_run: bool) -> None:
    action = "Would download" if dry_run else "Downloaded"
    print()
    print("=" * 55)
    print("  RISK-003 Attachment Mirror — Complete")
    print("=" * 55)
    print(f"  {action:16s}: {summary.downloaded}")
    print(f"  {'Already on disk':16s}: {summary.skipped}")
    print(f"  {'Failed':16s}: {summary.failed}")
    if summary.errors:
        print()
        print("  Failures:")
        for e in summary.errors:
            print(f"    • {e}")
    print("=" * 55)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mirror all Airtable submission attachments to local disk."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without touching the filesystem.",
    )
    args = parser.parse_args()

    summary = _run(dry_run=args.dry_run)
    _print_summary(summary, dry_run=args.dry_run)

    if summary.failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
