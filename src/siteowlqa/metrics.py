"""metrics.py — Vendor performance metrics and CSV export layer.

This module computes all metrics from the submission archive and
exports them as structured CSV files to output/.

Outputs produced:
    output/submission_history.csv    — one row per submission (master log)
    output/vendor_metrics.csv        — one row per vendor, aggregated
    output/processing_summary.csv    — one row per day, daily aggregation

Design:
    - Reads from archive.load_all_submission_records() (JSON files)
    - Also reads from archive.load_all_executions() for turnaround data
    - Pure computation — no SQL, no Airtable calls
    - Safe to call after every pipeline run (idempotent overwrite)
"""

from __future__ import annotations

import csv
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from siteowlqa.archive import Archive
from siteowlqa.models import VendorMetric

log = logging.getLogger(__name__)

# CSV output filenames
_SUBMISSION_HISTORY_CSV = "submission_history.csv"
_VENDOR_METRICS_CSV = "vendor_metrics.csv"
_PROCESSING_SUMMARY_CSV = "processing_summary.csv"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def refresh_all_metrics(archive: Archive, output_dir: Path) -> None:
    """Recompute and export all metric CSVs from the archive.

    This is the single call made after each pipeline run.
    All three CSV files are overwritten with the latest data.

    Args:
        archive:    The Archive instance.
        output_dir: Folder where CSV files are written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    submissions = archive.load_all_submission_records()
    executions = archive.load_all_executions()

    if not submissions:
        log.info("No submission records in archive yet — skipping metrics refresh.")
        return

    _export_submission_history(submissions, executions, output_dir)
    _export_vendor_metrics(submissions, executions, output_dir)
    _export_processing_summary(submissions, output_dir)

    log.info(
        "Metrics refreshed: %d submissions | output=%s",
        len(submissions), output_dir,
    )


# ---------------------------------------------------------------------------
# Submission history export
# ---------------------------------------------------------------------------

def _export_submission_history(
    submissions: list[dict[str, Any]],
    executions: list[dict[str, Any]],
    output_dir: Path,
) -> None:
    """Write submission_history.csv — one row per submission."""
    if not submissions:
        return

    turnaround: dict[str, float] = {}
    for ex in executions:
        sid = ex.get("submission_id", "")
        dur = ex.get("duration_seconds")
        if sid and dur is not None:
            turnaround[sid] = float(dur)

    for sub in submissions:
        sid = sub.get("submission_id", "")
        if sid in turnaround:
            sub["turnaround_seconds"] = turnaround[sid]

    # Enrich with turnaround_seconds when possible (from executions).
    # PASS submissions often store Score="PASS" in Airtable, so score may be blank here.
    fieldnames = [
        "submission_id", "record_id", "vendor_email", "vendor_name",
        "site_number", "attachment_filename", "submitted_at",
        "processed_at", "status", "score", "turnaround_seconds", "error_count",
        "output_report_path", "sql_project_key", "execution_id",
        "archived_file_path", "notes",
    ]

    path = output_dir / _SUBMISSION_HISTORY_CSV
    _write_csv(path, fieldnames, submissions)
    log.info("submission_history.csv updated: %d rows", len(submissions))


# ---------------------------------------------------------------------------
# Vendor metrics export
# ---------------------------------------------------------------------------

def _export_vendor_metrics(
    submissions: list[dict[str, Any]],
    executions: list[dict[str, Any]],
    output_dir: Path,
) -> None:
    """Write vendor_metrics.csv — one row per vendor."""
    # Build turnaround lookup: submission_id -> duration_seconds
    turnaround: dict[str, float] = {}
    for ex in executions:
        sid = ex.get("submission_id", "")
        dur = ex.get("duration_seconds")
        if sid and dur is not None:
            turnaround[sid] = float(dur)

    # Aggregate by vendor_email
    vendor_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sub in submissions:
        email = sub.get("vendor_email", "unknown")
        vendor_buckets[email].append(sub)

    metrics_rows: list[dict[str, Any]] = []
    for email, subs in sorted(vendor_buckets.items()):
        vm = _compute_vendor_metric(email, subs, turnaround)
        metrics_rows.append(vm.to_dict())

    fieldnames = [
        "vendor_email", "vendor_name", "total_submissions",
        "total_pass", "total_fail", "total_error",
        "pass_rate_pct", "fail_rate_pct", "avg_score_on_fail",
        "latest_submission_at", "avg_turnaround_seconds",
    ]
    path = output_dir / _VENDOR_METRICS_CSV
    _write_csv(path, fieldnames, metrics_rows)
    log.info("vendor_metrics.csv updated: %d vendors", len(metrics_rows))


def _compute_vendor_metric(
    email: str,
    subs: list[dict[str, Any]],
    turnaround: dict[str, float],
) -> VendorMetric:
    """Compute aggregated metrics for a single vendor."""
    vendor_name = subs[-1].get("vendor_name", "") or email
    total = len(subs)
    passed = sum(1 for s in subs if s.get("status") == "PASS")
    failed = sum(1 for s in subs if s.get("status") == "FAIL")
    errored = sum(1 for s in subs if s.get("status") == "ERROR")

    fail_scores = [
        float(s["score"]) for s in subs
        if s.get("status") == "FAIL" and s.get("score") is not None
    ]
    avg_fail_score = (
        sum(fail_scores) / len(fail_scores) if fail_scores else None
    )

    submission_ids = [s.get("submission_id", "") for s in subs]
    ta_values = [
        turnaround[sid] for sid in submission_ids if sid in turnaround
    ]
    avg_ta = sum(ta_values) / len(ta_values) if ta_values else None

    processed_times = [
        s.get("processed_at", "") for s in subs if s.get("processed_at")
    ]
    latest = max(processed_times) if processed_times else ""

    return VendorMetric(
        vendor_email=email,
        vendor_name=vendor_name,
        total_submissions=total,
        total_pass=passed,
        total_fail=failed,
        total_error=errored,
        pass_rate_pct=(passed / total * 100) if total else 0.0,
        fail_rate_pct=(failed / total * 100) if total else 0.0,
        avg_score_on_fail=avg_fail_score,
        latest_submission_at=latest,
        avg_turnaround_seconds=avg_ta,
    )


# ---------------------------------------------------------------------------
# Processing summary (daily rollup)
# ---------------------------------------------------------------------------

def _export_processing_summary(
    submissions: list[dict[str, Any]], output_dir: Path
) -> None:
    """Write processing_summary.csv — one row per calendar day."""
    daily: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "date": "",
            "total": 0,
            "pass": 0,
            "fail": 0,
            "error": 0,
            "avg_score": None,
            "unique_vendors": set(),
            "unique_sites": set(),
        }
    )

    for sub in submissions:
        ts = sub.get("processed_at", "")
        try:
            day = datetime.fromisoformat(ts).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            day = "unknown"

        bucket = daily[day]
        bucket["date"] = day
        bucket["total"] += 1

        status = sub.get("status", "")
        if status == "PASS":
            bucket["pass"] += 1
        elif status == "FAIL":
            bucket["fail"] += 1
        else:
            bucket["error"] += 1

        bucket["unique_vendors"].add(sub.get("vendor_email", ""))
        bucket["unique_sites"].add(sub.get("site_number", ""))

    rows = []
    for day in sorted(daily.keys()):
        b = daily[day]
        rows.append({
            "date": b["date"],
            "total_submissions": b["total"],
            "total_pass": b["pass"],
            "total_fail": b["fail"],
            "total_error": b["error"],
            "pass_rate_pct": (
                round(b["pass"] / b["total"] * 100, 2) if b["total"] else 0
            ),
            "unique_vendors": len(b["unique_vendors"]),
            "unique_sites": len(b["unique_sites"]),
        })

    fieldnames = [
        "date", "total_submissions", "total_pass", "total_fail",
        "total_error", "pass_rate_pct", "unique_vendors", "unique_sites",
    ]
    path = output_dir / _PROCESSING_SUMMARY_CSV
    _write_csv(path, fieldnames, rows)
    log.info("processing_summary.csv updated: %d day(s)", len(rows))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, Any]],
) -> None:
    """Write a list of dicts to a CSV file, overwriting if it exists."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=fieldnames, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)
