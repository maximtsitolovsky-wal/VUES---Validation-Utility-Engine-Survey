"""Mass regrade Airtable submissions against current SQL reference data.

Behavior:
- fetches Airtable records across PASS / FAIL / ERROR
- downloads each attachment
- replays normalization + site validation + Python grading
- patches Airtable Processing Status / Score / Fail Summary
- runs sequentially on purpose to keep the blast radius understandable

Usage:
    python regrade_all_airtable_submissions.py
    python regrade_all_airtable_submissions.py --max-records 50
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from siteowlqa.airtable_client import AirtableClient
from siteowlqa.config import STATUS_FAIL, STATUS_PASS, load_config
from siteowlqa.correction_state import CorrectionStateDB
from siteowlqa.file_processor import load_vendor_file_with_metadata
from siteowlqa.models import AirtableRecord, ProcessingStatus, SubmissionResult
from siteowlqa.poll_airtable import _build_fail_summary, _summarize_fail_issues
from siteowlqa.post_pass_correction import run_post_pass_correction
from siteowlqa.python_grader import (
    grade_submission_in_python,
    GradingInconsistencyError,
    status_from_score,
    validate_grading_consistency,
)
from siteowlqa.site_validation import validate_submission_for_site
from siteowlqa.utils import configure_logging, safe_delete

DEFAULT_STATUSES = {"PASS", "FAIL", "ERROR", "", "NEW", "Pending"}


@dataclass(slots=True)
class RegradeResult:
    submission_id: str
    record_id: str
    site_number: str
    old_status: str
    new_status: str
    old_score: str | None
    new_score: float | None
    changed: bool
    note: str = ""



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-records",
        type=int,
        default=0,
        help="Maximum Airtable records to regrade. 0 means all matching records.",
    )
    parser.add_argument(
        "--site-number",
        type=str,
        default="",
        help="If set, only regrade Airtable submissions for this Site Number.",
    )
    parser.add_argument(
        "--force-recorrect",
        action="store_true",
        help="Re-run post-pass correction even if record is already marked corrected.",
    )
    return parser.parse_args()



def normalize_airtable_score(status: str, score_value: str | None) -> str | None:
    if score_value in (None, ""):
        return STATUS_PASS if status == STATUS_PASS else None
    return str(score_value).strip()



def normalize_result_score(result: SubmissionResult) -> float | None:
    if result.status == ProcessingStatus.ERROR:
        return None
    return float(result.score) if result.score is not None else None



def fetch_all_records(
    airtable: AirtableClient,
    *,
    max_records: int,
    site_number: str,
) -> list[AirtableRecord]:
    # True "all submissions" means: fetch the whole table.
    records = airtable.list_all_records(max_records=max_records)
    if site_number:
        site_key = site_number.strip()
        records = [r for r in records if str(r.site_number).strip() == site_key]
    return records



def regrade_one(
    cfg,
    airtable: AirtableClient,
    record: AirtableRecord,
    correction_state: CorrectionStateDB,
    *,
    force_recorrect: bool = False,
) -> RegradeResult:
    attachment_path: Path | None = None
    old_status = record.processing_status.strip().upper()
    old_score: str | None = None
    # We don't currently parse these from AirtableRecord; leave None.
    old_fail_summary: str | None = None
    old_notes_internal: str | None = None
    old_fail_summary: str | None = None
    old_notes_internal: str | None = None

    try:
        attachment_path = airtable.download_attachment(record)
        load_result = load_vendor_file_with_metadata(attachment_path, record.site_number)
        validation = validate_submission_for_site(
            cfg=cfg,
            site_number=record.site_number,
            load_result=load_result,
        )

        error_df = None
        # Initialize required fields — must ALWAYS be set before writeback.
        notes_internal: str = ""
        true_score_value: float = 0.0

        if not validation.is_valid_for_grading:
            # Business rule: no ERRORs. Validation failure = FAIL with score 0.
            # Populate notes so Airtable never shows blanks.
            notes_internal = (
                f"SubmissionID={record.submission_id} | Site={record.site_number}\n"
                f"Validation failed before grading.\n"
                f"Reason codes: {', '.join(validation.reason_codes)}\n"
                f"Missing critical cols: {validation.missing_critical_columns or 'none'}\n"
                f"Reference rows: {validation.reference_row_count} | "
                f"Submitted rows: {validation.normalized_row_count}"
            )
            true_score_value = 0.0
            result = SubmissionResult(
                submission_id=record.submission_id,
                status=ProcessingStatus.FAIL,
                score=0.0,
                message="; ".join(validation.reason_codes),
            )
        else:
            grade_outcome = grade_submission_in_python(
                cfg=cfg,
                submission_df=load_result.dataframe,
                submission_id=record.submission_id,
                site_number=record.site_number,
                survey_type=record.survey_type,
            )
            result = grade_outcome.result
            error_df = grade_outcome.error_df
            notes_internal = grade_outcome.notes_internal or ""
            # True Score is always the raw numeric value from the grader.
            true_score_value = float(result.score) if result.score is not None else 0.0

        new_score = normalize_result_score(result)
        note = result.message or ""
        # Use result.status for note-building only; authoritative status comes from
        # status_from_score() below and may differ from result.status.
        if result.status == ProcessingStatus.FAIL and error_df is not None and not error_df.empty:
            issue_lines = _summarize_fail_issues(error_df)
            if issue_lines:
                note = " | ".join(line.strip() for line in issue_lines[:3])[:500]

        fail_summary = _build_fail_summary(result, error_df)

        # RULE: status is ALWAYS re-derived from true_score_value.
        # Never propagate result.status directly — it may reflect stale reference data.
        fresh_status = status_from_score(true_score_value)
        if fresh_status != result.status:
            log.warning(
                "GRADING_INCONSISTENCY (regrade): grader returned status=%s but "
                "score-derived status=%s for submission=%s true_score=%.4f. "
                "Overriding to score-derived status.",
                result.status.value, fresh_status.value, record.submission_id, true_score_value,
            )
        new_status = fresh_status.value
        validate_grading_consistency(
            true_score=true_score_value,
            status=fresh_status,
            context=f"regrade submission={record.submission_id}",
        )

        if not notes_internal.strip():
            notes_internal = (
                f"SubmissionID={record.submission_id} | Site={record.site_number}\n"
                f"Auto-generated regrade diagnostics.\n"
                f"Status={new_status} | TrueScore={true_score_value}"
            )

        airtable_status = STATUS_PASS if new_status == STATUS_PASS else STATUS_FAIL

        changed = True

        if changed:
            airtable.update_result(
                record_id=record.record_id,
                status=airtable_status,
                score=true_score_value,   # always numeric — never None
                fail_summary=fail_summary,
                notes_internal=notes_internal,
                true_score=true_score_value,
            )
        else:
            logging.getLogger(__name__).info(
                "No change for %s (record=%s) status=%s; skipping Airtable writeback.",
                record.submission_id,
                record.record_id,
                old_status,
            )

        # Canonical workflow: run post-pass correction after successful PASS writeback.
        if fresh_status == ProcessingStatus.PASS:
            already_corrected = correction_state.is_corrected(record.record_id)
            if already_corrected and not force_recorrect:
                logging.getLogger(__name__).info(
                    "Post-pass correction skipped (already corrected): record=%s submission=%s",
                    record.record_id,
                    record.submission_id,
                )
            else:
                correction_summary = run_post_pass_correction(
                    cfg=cfg,
                    submission_id=record.submission_id,
                    site_number=record.site_number,
                    vendor_name=record.vendor_name,
                    true_score=true_score_value,
                    archived_file_path=attachment_path,
                )
                if correction_summary is not None:
                    correction_state.mark_corrected(
                        record.record_id,
                        submission_id=record.submission_id,
                        site_number=record.site_number,
                        vendor_name=record.vendor_name,
                        true_score=true_score_value,
                        corrected_csv_path=correction_summary.corrected_csv_path,
                        correction_log_path=correction_summary.correction_log_path,
                    )
                    print(
                        f"  correction: applied={correction_summary.total_corrections} "
                        f"review_flags={correction_summary.total_review_flags}"
                    )
        print(
            f"REGRADED {record.submission_id} | site={record.site_number} | "
            f"{old_status} -> {new_status} | score={new_score}"
        )
        if note:
            print(f"  note: {note}")
        return RegradeResult(
            submission_id=record.submission_id,
            record_id=record.record_id,
            site_number=record.site_number,
            old_status=old_status,
            new_status=new_status,
            old_score=old_score,
            new_score=new_score,
            changed=changed,
            note=note,
        )
    except Exception as exc:  # noqa: BLE001
        note = str(exc)
        print(
            f"FAILED {record.submission_id} | site={record.site_number} | "
            f"old={old_status} | error={note}"
        )
        # Business rule: no ERRORs. Write all required fields even on exception.
        failure_notes = (
            f"SubmissionID={record.submission_id} | Site={record.site_number}\n"
            f"Regrade exception — grading could not complete.\n"
            f"Error: {note[:1000]}"
        )
        try:
            airtable.update_result(
                record_id=record.record_id,
                status=STATUS_FAIL,
                score=0.0,
                fail_summary=f"Regrade error: {note[:400]}",
                notes_internal=failure_notes,
                true_score=0.0,
            )
        except Exception as write_exc:  # noqa: BLE001
            logging.getLogger(__name__).error(
                "Could not write failure result for record %s: %s",
                record.record_id, write_exc,
            )
        return RegradeResult(
            submission_id=record.submission_id,
            record_id=record.record_id,
            site_number=record.site_number,
            old_status=old_status,
            new_status=STATUS_FAIL,
            old_score=old_score,
            new_score=0.0,
            changed=True,
            note=note,
        )
    finally:
        safe_delete(attachment_path)



def print_summary(results: list[RegradeResult]) -> None:
    changed = [r for r in results if r.changed]
    failed = [r for r in results if r.note and r.new_status == "ERROR" and "FAILED" not in r.note]
    print()
    print("=== Airtable Regrade Complete ===")
    print(f"Total records processed: {len(results)}")
    print(f"Changed statuses: {len(changed)}")
    print(f"Unchanged statuses: {len(results) - len(changed)}")
    print(f"Records with notes/errors: {len([r for r in results if r.note])}")



def main() -> int:
    args = parse_args()
    logs_dir = ROOT / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    configure_logging(logs_dir)
    logging.getLogger(__name__).info("Starting Airtable mass regrade.")

    cfg = load_config()
    airtable = AirtableClient(cfg)
    correction_state = CorrectionStateDB(cfg.output_dir / "corrections")
    records = fetch_all_records(
        airtable,
        max_records=max(0, args.max_records),
        site_number=args.site_number,
    )
    if not records:
        print("No Airtable records found for regrading.")
        return 0

    print(f"Processing {len(records)} records from Airtable...\n")
    results = []
    for idx, record in enumerate(records, 1):
        print(f"[{idx}/{len(records)}] {record.record_id} site={record.site_number} status={record.processing_status}")
        result = regrade_one(
            cfg,
            airtable,
            record,
            correction_state,
            force_recorrect=args.force_recorrect,
        )
        results.append(result)
    
    print_summary(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
