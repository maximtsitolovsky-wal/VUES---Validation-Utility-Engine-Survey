"""Reprocess archived submissions currently marked ERROR using Python-first grading.

Behavior:
- targets only archive metadata rows with status=ERROR
- runs sequentially on purpose
- uses site-scoped Python comparison rules
- updates archive metadata and attempts Airtable writeback
- regenerates metrics from archive after completion

Usage:
    python reprocess_error_submissions.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from siteowlqa.airtable_client import AirtableClient
from siteowlqa.archive import Archive
from siteowlqa.config import STATUS_ERROR, STATUS_FAIL, STATUS_PASS, load_config
from siteowlqa.file_processor import load_vendor_file_with_metadata
from siteowlqa.metrics import refresh_all_metrics
from siteowlqa.models import ProcessingStatus, SubmissionResult
from siteowlqa.poll_airtable import _build_fail_summary, _summarize_fail_issues
from siteowlqa.python_grader import grade_submission_in_python
from siteowlqa.site_validation import validate_submission_for_site

ARCHIVE_ROOT = Path("archive/submissions")


@dataclass(slots=True)
class ReprocessOutcome:
    submission_id: str
    record_id: str
    site_number: str
    old_status: str
    new_status: str
    old_score: float | None
    new_score: float | None
    changed: bool
    note: str = ""


@dataclass(slots=True)
class CanonicalReplay:
    result: SubmissionResult
    raw_score: float | None
    error_df_count: int



def main() -> None:
    cfg = load_config()
    airtable = AirtableClient(cfg)
    archive = Archive(cfg.archive_dir)

    outcomes: list[ReprocessOutcome] = []
    for meta_path in sorted(ARCHIVE_ROOT.rglob("*_meta.json")):
        if not is_error_meta(meta_path):
            continue
        outcomes.append(reprocess_one(cfg, airtable, meta_path))

    refresh_all_metrics(archive, cfg.output_dir)
    print_summary(outcomes)



def is_error_meta(meta_path: Path) -> bool:
    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)
    return str(meta.get("status") or "").strip().upper() == "ERROR"



def reprocess_one(cfg, airtable: AirtableClient, meta_path: Path) -> ReprocessOutcome:
    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)

    submission_id = str(meta.get("submission_id") or "").strip()
    record_id = str(meta.get("record_id") or "").strip()
    site_number = str(meta.get("site_number") or "").strip()
    vendor_email = str(meta.get("vendor_email") or "").strip()
    old_status = str(meta.get("status") or "").strip().upper()
    old_score = normalize_archive_score(old_status, meta.get("score"))

    raw_file = Path(str(meta.get("archived_file_path") or "").strip())
    if not raw_file.exists():
        return persist_and_patch(
            airtable=airtable,
            meta=meta,
            meta_path=meta_path,
            replay=CanonicalReplay(
                result=SubmissionResult(
                    submission_id=submission_id,
                    status=ProcessingStatus.ERROR,
                    score=None,
                    message=f"Archived raw file missing: {raw_file}",
                ),
                raw_score=None,
                error_df_count=0,
            ),
            old_status=old_status,
            old_score=old_score,
        )

    load_result = load_vendor_file_with_metadata(raw_file, site_number)
    validation = validate_submission_for_site(cfg, site_number, load_result)

    error_df = None
    if not validation.is_valid_for_grading:
        replay = CanonicalReplay(
            result=SubmissionResult(
                submission_id=submission_id,
                status=ProcessingStatus.ERROR,
                score=None,
                message="; ".join(validation.reason_codes),
            ),
            raw_score=None,
            error_df_count=0,
        )
    else:
        outcome = grade_submission_in_python(
            cfg=cfg,
            submission_df=load_result.dataframe,
            submission_id=submission_id,
            site_number=site_number,
        )
        error_df = outcome.error_df
        replay = CanonicalReplay(
            result=outcome.result,
            raw_score=outcome.result.score,
            error_df_count=len(error_df) if error_df is not None else 0,
        )
    return persist_and_patch(
        airtable=airtable,
        meta=meta,
        meta_path=meta_path,
        replay=replay,
        old_status=old_status,
        old_score=old_score,
        error_df=error_df,
    )



def persist_and_patch(
    airtable: AirtableClient,
    meta: dict,
    meta_path: Path,
    replay: CanonicalReplay,
    old_status: str,
    old_score: float | None,
    error_df=None,
) -> ReprocessOutcome:
    record_id = str(meta.get("record_id") or "").strip()
    submission_id = str(meta.get("submission_id") or "").strip()
    site_number = str(meta.get("site_number") or "").strip()

    new_status = replay.result.status.value
    new_score = normalize_result_score(replay.result)
    note = replay.result.message or ""
    error_count = replay.error_df_count
    if new_status == "FAIL" and error_df is not None and not error_df.empty:
        issue_lines = _summarize_fail_issues(error_df)
        if issue_lines:
            note = " | ".join(line.strip() for line in issue_lines[:3])[:500]

    meta["status"] = new_status
    meta["score"] = new_score
    meta["error_count"] = error_count
    meta["notes"] = note[:500]

    airtable_status = (
        STATUS_PASS if new_status == "PASS"
        else STATUS_FAIL if new_status == "FAIL"
        else STATUS_ERROR
    )
    fail_summary = _build_fail_summary(replay.result, error_df)
    writeback_score = replay.raw_score if new_status == "FAIL" else None
    try:
        airtable.update_result(
            record_id=record_id,
            status=airtable_status,
            score=writeback_score,
            fail_summary=fail_summary,
        )
        if new_status == "PASS":
            airtable.patch_score(record_id, STATUS_PASS)
    except Exception as exc:  # noqa: BLE001
        note = (note + " | " if note else "") + f"Airtable patch skipped: {exc}"
        meta["notes"] = note[:500]

    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    changed = old_status != new_status or old_score != new_score
    print(
        f"REPROCESSED {submission_id} | site={site_number} | "
        f"{old_status}/{old_score} -> {new_status}/{new_score}"
    )
    if note:
        print(f"  note: {note}")

    return ReprocessOutcome(
        submission_id=submission_id,
        record_id=record_id,
        site_number=site_number,
        old_status=old_status,
        new_status=new_status,
        old_score=old_score,
        new_score=new_score,
        changed=changed,
        note=note,
    )



def normalize_archive_score(status: str, raw_score) -> float | None:
    if status == "PASS" and raw_score in (None, ""):
        return 100.0
    if raw_score in (None, ""):
        return None
    return round(float(raw_score), 2)



def normalize_result_score(result: SubmissionResult) -> float | None:
    if result.status == ProcessingStatus.PASS:
        return 100.0
    if result.status == ProcessingStatus.ERROR:
        return None
    return round(float(result.score), 2) if result.score is not None else None



def print_summary(outcomes: list[ReprocessOutcome]) -> None:
    changed = [o for o in outcomes if o.changed]
    print()
    print("=== ERROR Reprocess Complete ===")
    print(f"Total ERROR submissions processed: {len(outcomes)}")
    print(f"Changed outcomes: {len(changed)}")
    print(f"Unchanged outcomes: {len(outcomes) - len(changed)}")


if __name__ == "__main__":
    main()
