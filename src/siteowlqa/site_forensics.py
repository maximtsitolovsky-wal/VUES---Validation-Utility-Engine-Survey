"""Forensic comparison of archived submissions against live reference data.

For each archived submission this script reports:
- raw file columns
- missing required vendor columns after normalization
- normalized row count
- live reference row count for the site
- replay outcome under current grading logic

This helps separate:
- valid FAILs (data comparable, score < 95)
- invalid submissions (missing columns / bad row counts / no reference)

Usage:
    python site_forensics.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from siteowlqa.config import VENDOR_REQUIRED_COLUMNS, load_config
from siteowlqa.file_processor import load_vendor_file_with_metadata
from siteowlqa.models import ProcessingStatus
from siteowlqa.site_validation import validate_submission_for_site
from siteowlqa.sql import get_connection, run_full_pipeline

ARCHIVE_ROOT = Path("archive/submissions")


@dataclass(slots=True)
class ForensicRow:
    submission_id: str
    site_number: str
    archived_status: str
    archived_score: str
    raw_columns: list[str]
    missing_columns: list[str]
    normalized_rows: int
    reference_rows: int
    validation_status: str
    validation_reasons: list[str]
    replay_status: str
    replay_score: str
    error_count: int


def main() -> None:
    cfg = load_config()
    meta_files = sorted(ARCHIVE_ROOT.rglob("*_meta.json"))
    rows: list[ForensicRow] = []

    for meta_path in meta_files:
        rows.append(analyze_submission(cfg, meta_path))

    print_summary(rows)


def analyze_submission(cfg, meta_path: Path) -> ForensicRow:
    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)

    submission_id = str(meta.get("submission_id") or "").strip()
    site_number = str(meta.get("site_number") or "").strip()
    vendor_email = str(meta.get("vendor_email") or "").strip()
    archived_status = str(meta.get("status") or "").strip().upper()
    archived_score = str(meta.get("score") or "").strip()
    raw_file = Path(str(meta.get("archived_file_path") or "").strip())

    raw_columns: list[str] = []
    missing_columns: list[str] = []
    normalized_rows = 0
    reference_rows = get_reference_row_count(cfg, site_number)
    validation_status = "ERROR"
    validation_reasons: list[str] = []
    replay_status = "ERROR"
    replay_score = ""
    error_count = 0

    if raw_file.exists():
        raw_columns = read_raw_columns(raw_file)
        missing_columns = [c for c in VENDOR_REQUIRED_COLUMNS if c not in raw_columns]
        load_result = load_vendor_file_with_metadata(raw_file, site_number)
        normalized_rows = len(load_result.dataframe)
        validation = validate_submission_for_site(cfg, site_number, load_result)
        validation_status = validation.status
        validation_reasons = validation.reason_codes

        if validation.is_valid_for_grading:
            result, error_df = run_full_pipeline(
                cfg=cfg,
                df=load_result.dataframe,
                submission_id=submission_id,
                vendor_email=vendor_email,
                site_number=site_number,
            )
            replay_status = result.status.value
            replay_score = format_replay_score(result.status, result.score)
            error_count = len(error_df) if error_df is not None else 0

    return ForensicRow(
        submission_id=submission_id,
        site_number=site_number,
        archived_status=archived_status,
        archived_score=archived_score,
        raw_columns=raw_columns,
        missing_columns=missing_columns,
        normalized_rows=normalized_rows,
        reference_rows=reference_rows,
        validation_status=validation_status,
        validation_reasons=validation_reasons,
        replay_status=replay_status,
        replay_score=replay_score,
        error_count=error_count,
    )


def read_raw_columns(raw_file: Path) -> list[str]:
    if raw_file.suffix.lower() == ".xlsx":
        df = pd.read_excel(raw_file, sheet_name=0, dtype=str, engine="openpyxl")
    else:
        df = pd.read_csv(raw_file, dtype=str)
    return [str(c).strip() for c in df.columns]


def get_reference_row_count(cfg, site_number: str) -> int:
    with get_connection(cfg, autocommit=False) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM dbo.vw_ReferenceNormalized WHERE ProjectID = ?",
            (site_number,),
        )
        return int(cur.fetchone()[0])


def format_replay_score(status: ProcessingStatus, score: float | None) -> str:
    if status == ProcessingStatus.PASS:
        return "100.0"
    if score is None:
        return ""
    return f"{score:.2f}"


def print_summary(rows: list[ForensicRow]) -> None:
    print("=== Site Forensics ===")
    for row in rows:
        print(
            f"{row.submission_id} | site={row.site_number} | "
            f"archived={row.archived_status}/{row.archived_score or '-'} | "
            f"validation={row.validation_status} | "
            f"replay={row.replay_status}/{row.replay_score or '-'} | "
            f"norm_rows={row.normalized_rows} | ref_rows={row.reference_rows} | "
            f"missing_cols={len(row.missing_columns)} | errors={row.error_count}"
        )
        if row.validation_reasons:
            print(f"  validation reasons: {row.validation_reasons}")
        if row.missing_columns:
            print(f"  missing: {row.missing_columns}")
        if row.raw_columns:
            print(f"  raw cols: {row.raw_columns}")


if __name__ == "__main__":
    main()
