"""Bulk regrade archived submissions using Python-first site-indexed grading.

This script runs sequentially on purpose so archive updates and Airtable
patches stay easy to inspect.

Actions:
- load archived submission metadata
- validate each archived raw file against the site reference profile
- when valid, replay through the Python grader
- rewrite archive metadata with corrected status/score/error_count/notes
- patch Airtable status/score/fail summary for the corresponding record
- regenerate submission_history.csv and related metrics from archive

Usage:
    python bulk_regrade_corrected_submissions.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from siteowlqa.airtable_client import AirtableClient
from siteowlqa.archive import Archive
from siteowlqa.config import STATUS_FAIL, STATUS_PASS, load_config
from siteowlqa.file_processor import load_vendor_file_with_metadata
from siteowlqa.models import ProcessingStatus, SubmissionResult
from siteowlqa.metrics import refresh_all_metrics
from siteowlqa.poll_airtable import _build_fail_summary, _summarize_fail_issues
from siteowlqa.python_grader import (
    grade_submission_in_python,
    GradingInconsistencyError,
    status_from_score,
    validate_grading_consistency,
)
from siteowlqa.site_validation import validate_submission_for_site

ARCHIVE_ROOT = Path("archive/submissions")


@dataclass(slots=True)
class RegradeOutcome:
    submission_id: str
    record_id: str
    site_number: str
    old_status: str
    new_status: str
    old_score: float | None
    new_score: float | None
    changed: bool
    note: str = ""


def main() -> None:
    cfg = load_config()
    airtable = AirtableClient(cfg)
    archive = Archive(cfg.archive_dir)

    outcomes: list[RegradeOutcome] = []
    for meta_path in sorted(ARCHIVE_ROOT.rglob("*_meta.json")):
        outcomes.append(regrade_one(cfg, airtable, meta_path))

    refresh_all_metrics(archive, cfg.output_dir)
    print_summary(outcomes)


def regrade_one(cfg, airtable: AirtableClient, meta_path: Path) -> RegradeOutcome:
    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)

    submission_id = str(meta.get("submission_id") or "").strip()
    record_id = str(meta.get("record_id") or "").strip()
    site_number = str(meta.get("site_number") or "").strip()
    old_status = str(meta.get("status") or "").strip().upper()
    old_score = normalize_archive_score(old_status, meta.get("score"))

    archived_file_path = str(meta.get("archived_file_path") or "").strip()
    raw_file = Path(archived_file_path)
    if not raw_file.exists():
        return persist_and_patch(
            airtable=airtable,
            meta=meta,
            meta_path=meta_path,
            new_status="ERROR",
            new_score=None,
            error_count=0,
            note=f"Archived raw file missing: {raw_file}",
            notes_internal=(
                f"SubmissionID={submission_id or '<missing>'} | Site={site_number or '<missing>'}\n"
                f"Archived raw file missing.\n"
                f"Path: {raw_file}"
            ),
            true_score=0.0,
            old_status=old_status,
            old_score=old_score,
        )

    load_result = load_vendor_file_with_metadata(raw_file, site_number)
    validation = validate_submission_for_site(cfg, site_number, load_result)
    if not validation.is_valid_for_grading:
        return persist_and_patch(
            airtable=airtable,
            meta=meta,
            meta_path=meta_path,
            new_status="ERROR",
            new_score=None,
            error_count=0,
            note="; ".join(validation.reason_codes),
            notes_internal=(
                f"SubmissionID={submission_id} | Site={site_number}\n"
                f"Validation failed before grading.\n"
                f"Reason codes: {', '.join(validation.reason_codes)}"
            ),
            true_score=0.0,
            old_status=old_status,
            old_score=old_score,
        )

    outcome = grade_submission_in_python(
        cfg=cfg,
        submission_df=load_result.dataframe,
        submission_id=submission_id,
        site_number=site_number,
    )
    result = outcome.result
    error_df = outcome.error_df
    true_score = float(result.score) if result.score is not None else 0.0

    # RULE: status is ALWAYS re-derived from true_score.
    # Never propagate result.status directly — it may reflect stale reference data.
    fresh_status = status_from_score(true_score)
    if fresh_status != result.status:
        import logging as _log
        _log.getLogger(__name__).warning(
            "GRADING_INCONSISTENCY (bulk-regrade): grader returned status=%s but "
            "score-derived status=%s for submission=%s true_score=%.4f. Overriding.",
            result.status.value, fresh_status.value, submission_id, true_score,
        )
    validate_grading_consistency(
        true_score=true_score,
        status=fresh_status,
        context=f"bulk-regrade submission={submission_id}",
    )

    new_status = fresh_status.value
    new_score = true_score  # always numeric — never None for a graded submission
    error_count = len(error_df) if error_df is not None else 0
    note = result.message or ""
    if fresh_status == ProcessingStatus.FAIL and error_df is not None and not error_df.empty:
        issue_lines = _summarize_fail_issues(error_df)
        if issue_lines:
            note = " | ".join(line.strip() for line in issue_lines[:3])[:500]

    notes_internal = outcome.notes_internal or (
        f"SubmissionID={submission_id} | Site={site_number}\n"
        f"Auto-generated archived regrade diagnostics.\n"
        f"Status={new_status} | TrueScore={true_score}"
    )

    return persist_and_patch(
        airtable=airtable,
        meta=meta,
        meta_path=meta_path,
        new_status=new_status,
        new_score=new_score,
        error_count=error_count,
        note=note,
        notes_internal=notes_internal,
        true_score=true_score,
        old_status=old_status,
        old_score=old_score,
        submission_result=result,
        error_df=error_df,
    )


def persist_and_patch(
    airtable: AirtableClient,
    meta: dict,
    meta_path: Path,
    new_status: str,
    new_score: float | None,
    error_count: int,
    note: str,
    notes_internal: str,
    true_score: float | None,
    old_status: str,
    old_score: float | None,
    submission_result: SubmissionResult | None = None,
    error_df=None,
) -> RegradeOutcome:
    record_id = str(meta.get("record_id") or "").strip()
    submission_id = str(meta.get("submission_id") or "").strip()
    site_number = str(meta.get("site_number") or "").strip()

    meta["status"] = new_status
    meta["score"] = new_score
    meta["error_count"] = error_count
    meta["notes"] = note[:500]

    if submission_result is None:
        submission_result = SubmissionResult(
            submission_id=submission_id,
            status=ProcessingStatus(new_status),
            score=new_score,
            message=note,
        )

    # ERROR cases fall back to STATUS_FAIL in Airtable (no ERROR status in Airtable).
    airtable_status = STATUS_PASS if new_status == "PASS" else STATUS_FAIL
    fail_summary = _build_fail_summary(submission_result, error_df)
    # Score always numeric — None only for ERROR cases (missing file, etc.)
    try:
        airtable.update_result(
            record_id=record_id,
            status=airtable_status,
            score=new_score,   # always numeric for graded results, None for errors
            fail_summary=fail_summary,
            notes_internal=notes_internal,
            true_score=true_score,
        )
    except Exception as exc:  # noqa: BLE001
        note = (note + " | " if note else "") + f"Airtable patch skipped: {exc}"

    meta["notes"] = note[:500]
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    changed = old_status != new_status or old_score != new_score
    print(
        f"UPDATED {submission_id} | site={site_number} | "
        f"{old_status}/{old_score} -> {new_status}/{new_score}"
    )
    if note:
        print(f"  note: {note}")

    return RegradeOutcome(
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


def print_summary(outcomes: list[RegradeOutcome]) -> None:
    changed = [o for o in outcomes if o.changed]
    print()
    print("=== Bulk Regrade Complete ===")
    print(f"Total archived submissions: {len(outcomes)}")
    print(f"Changed outcomes: {len(changed)}")
    print(f"Unchanged outcomes: {len(outcomes) - len(changed)}")


if __name__ == "__main__":
    main()
