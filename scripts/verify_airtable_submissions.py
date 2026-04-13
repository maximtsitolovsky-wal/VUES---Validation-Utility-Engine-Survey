"""Dry-run verifier for Airtable submissions.

Purpose:
- Pull real Airtable submissions without mutating Airtable.
- Replay normalization + site validation + SQL grading.
- Compare replayed outcomes to Airtable's current recorded status/score.
- Surface mismatches so grading logic changes can be validated safely.

This script intentionally does NOT:
- update Airtable
- send emails
- rewrite archive metadata
- republish dashboards

Usage examples:
    python verify_airtable_submissions.py
    python verify_airtable_submissions.py --max-records 10
    python verify_airtable_submissions.py --statuses PASS FAIL ERROR
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from siteowlqa.airtable_client import AirtableClient
from siteowlqa.config import STATUS_PASS, load_config
from siteowlqa.file_processor import load_vendor_file_with_metadata
from siteowlqa.models import AirtableRecord, ProcessingStatus
from siteowlqa.site_validation import validate_submission_for_site
from siteowlqa.sql import run_full_pipeline
from siteowlqa.utils import configure_logging, safe_delete

DEFAULT_STATUSES = ("PASS", "FAIL", "ERROR")


@dataclass(slots=True)
class VerificationResult:
    submission_id: str
    record_id: str
    site_number: str
    airtable_status: str
    airtable_score: str | None
    replay_status: str
    replay_score: float | None
    error_count: int
    matched: bool
    note: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-records", type=int, default=10)
    parser.add_argument(
        "--statuses",
        nargs="+",
        default=list(DEFAULT_STATUSES),
        help="Airtable statuses to fetch for replay, e.g. PASS FAIL ERROR",
    )
    return parser.parse_args()


def normalize_airtable_score(status: str, raw_score: Any) -> str | None:
    if raw_score in (None, ""):
        return STATUS_PASS if status == STATUS_PASS else None
    return str(raw_score).strip()


def normalize_replay_score(status: ProcessingStatus, raw_score: float | None) -> float | None:
    if status == ProcessingStatus.PASS:
        return 100.0
    if status == ProcessingStatus.ERROR:
        return None
    return round(float(raw_score), 2) if raw_score is not None else None


def statuses_match(airtable_status: str, replay_status: str) -> bool:
    return airtable_status.strip().upper() == replay_status.strip().upper()


def score_matches(airtable_status: str, airtable_score: str | None, replay_score: float | None) -> bool:
    normalized_status = airtable_status.strip().upper()
    if normalized_status == STATUS_PASS:
        return replay_score == 100.0
    if normalized_status == "ERROR":
        return replay_score is None
    if airtable_score in (None, "") and replay_score is None:
        return True
    try:
        if airtable_score is None:
            return False
        clean = airtable_score.replace("%", "").strip()
        return round(float(clean), 2) == round(float(replay_score), 2)
    except Exception:
        return False


def fetch_airtable_status_and_score(cfg, record_id: str) -> tuple[str, str | None]:
    import requests

    from airtable_client import AIRTABLE_API_BASE
    from config import ATAIRTABLE_FIELDS as FIELDS

    url = f"{AIRTABLE_API_BASE}/{cfg.airtable_base_id}/{requests.utils.quote(cfg.airtable_table_name, safe='')}/{record_id}"
    headers = {
        "Authorization": f"Bearer {cfg.airtable_token}",
        "Content-Type": "application/json",
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    fields = resp.json().get("fields", {})
    status = str(fields.get(FIELDS.status, "")).strip().upper()
    score_raw = fields.get(FIELDS.score)
    score = None if score_raw in (None, "") else str(score_raw).strip()
    return status, score


def verify_record(cfg, airtable: AirtableClient, record: AirtableRecord) -> VerificationResult:
    attachment_path: Path | None = None
    try:
        airtable_status, airtable_score = fetch_airtable_status_and_score(cfg, record.record_id)
        attachment_path = airtable.download_attachment(record)
        load_result = load_vendor_file_with_metadata(attachment_path, record.site_number)
        validation = validate_submission_for_site(
            cfg=cfg,
            site_number=record.site_number,
            load_result=load_result,
        )
        if not validation.is_valid_for_grading:
            return VerificationResult(
                submission_id=record.submission_id,
                record_id=record.record_id,
                site_number=record.site_number,
                airtable_status=airtable_status,
                airtable_score=normalize_airtable_score(airtable_status, airtable_score),
                replay_status="ERROR",
                replay_score=None,
                error_count=0,
                matched=(airtable_status == "ERROR"),
                note="; ".join(validation.reason_codes),
            )

        result, error_df = run_full_pipeline(
            cfg=cfg,
            df=load_result.dataframe,
            submission_id=record.submission_id,
            vendor_email=record.vendor_email,
            site_number=record.site_number,
        )
        replay_status = result.status.value
        replay_score = normalize_replay_score(result.status, result.score)
        error_count = len(error_df) if error_df is not None else 0
        normalized_airtable_score = normalize_airtable_score(airtable_status, airtable_score)
        matched = statuses_match(airtable_status, replay_status) and score_matches(
            airtable_status,
            normalized_airtable_score,
            replay_score,
        )
        return VerificationResult(
            submission_id=record.submission_id,
            record_id=record.record_id,
            site_number=record.site_number,
            airtable_status=airtable_status,
            airtable_score=normalized_airtable_score,
            replay_status=replay_status,
            replay_score=replay_score,
            error_count=error_count,
            matched=matched,
        )
    except Exception as exc:  # noqa: BLE001
        return VerificationResult(
            submission_id=record.submission_id,
            record_id=record.record_id,
            site_number=record.site_number,
            airtable_status="UNKNOWN",
            airtable_score=None,
            replay_status="ERROR",
            replay_score=None,
            error_count=0,
            matched=False,
            note=str(exc),
        )
    finally:
        safe_delete(attachment_path)


def print_results(results: list[VerificationResult]) -> int:
    print("=== Airtable Submission Verification ===")
    print(f"Total verified: {len(results)}")
    mismatches = [r for r in results if not r.matched]
    print(f"Matches: {len(results) - len(mismatches)}")
    print(f"Mismatches: {len(mismatches)}")
    print()

    for r in results:
        badge = "OK   " if r.matched else "MISM "
        print(
            f"{badge}{r.submission_id} | site={r.site_number} | "
            f"airtable={r.airtable_status}/{r.airtable_score} | "
            f"replay={r.replay_status}/{r.replay_score} | errors={r.error_count}"
        )
        if r.note:
            print(f"     note: {r.note}")

    return 1 if mismatches else 0


def main() -> int:
    args = parse_args()
    logs_dir = ROOT / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    configure_logging(logs_dir)
    logging.getLogger(__name__).info("Starting Airtable submission verification.")

    cfg = load_config()
    airtable = AirtableClient(cfg)
    statuses = {s.strip().upper() for s in args.statuses if s.strip()}
    records = airtable.list_records_for_testing(
        max_records=max(1, args.max_records),
        statuses=statuses,
    )

    if not records:
        print("No Airtable records found for verification.")
        return 0

    results = [verify_record(cfg, airtable, record) for record in records]
    return print_results(results)


if __name__ == "__main__":
    raise SystemExit(main())
