"""poll_airtable.py — Per-record submission processor.

Handles one Airtable record through the full 14-step QA pipeline:
    validate → memory check → download → normalize → site-scoped Python grade
    → email → Airtable status → submission archive → review → execution
    archive → lesson extraction

Metrics refresh is handled asynchronously by MetricsRefreshWorker in main.py.
All exceptions are caught per-record. One bad record NEVER crashes the loop.
The main poll loop lives in main.py.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from siteowlqa.archive import Archive, extract_lesson_from_failure
from siteowlqa.airtable_client import AirtableClient
from siteowlqa.config import AppConfig, STATUS_FAIL, STATUS_PASS, should_run_post_pass_correction
from siteowlqa.correction_state import CorrectionStateDB
from siteowlqa.file_processor import load_vendor_file_with_metadata
from siteowlqa.post_pass_correction import run_post_pass_correction
from siteowlqa.python_grader import (
    grade_submission_in_python,
    GradingInconsistencyError,
    status_from_score,
    validate_grading_consistency,
)
from siteowlqa.memory import Memory
from siteowlqa.models import (
    AirtableRecord, ExecutionRecord, ProcessingStatus,
    SubmissionArchiveRecord, SubmissionResult,
)
from siteowlqa.reviewer import review_pipeline_run
from siteowlqa.site_validation import validate_submission_for_site
from siteowlqa.utils import new_execution_id, safe_delete

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Primary record processor
# ---------------------------------------------------------------------------

def process_record(
    record: AirtableRecord,
    cfg: AppConfig,
    airtable: AirtableClient,
    archive: Archive,
    memory: Memory,
    correction_state: CorrectionStateDB | None = None,
) -> None:
    """Process one Airtable submission record through the full QA pipeline.

    Steps:
     1. Validate critical fields
     2. Consult memory for known risk patterns
     3. Download vendor attachment
     4. Normalise file, overwrite Project ID with Site Number
     5. Fetch site-scoped reference rows from SQL
     6. Compare only matching canonical headers in Python
     7. Derive PASS / FAIL / ERROR and score in Python
     8. Send vendor email (PASS / FAIL / ERROR)
     9. Update Airtable Processing Status
    10. Archive raw submission file + metadata
    11. Run internal reviewer on this run
    12. Archive execution record + review JSON
    13. Extract lesson from failures if actionable
    14. (reserved)
    15. Post-pass correction (downstream only)

    Note: metrics/dashboard refresh is NOT done here.
    The MetricsRefreshWorker handles that asynchronously after mark_dirty().
    """
    execution_id = new_execution_id()
    start_time = time.monotonic()
    attachment_path: Path | None = None
    rows_loaded: int = 0
    error_count: int = 0
    # Business rule: avoid ERROR statuses in Airtable.
    final_status = ProcessingStatus.FAIL
    score: float | None = None
    error_message: str = ""
    output_report_path: str = ""
    # These MUST always be populated before writeback — no exceptions.
    notes_internal: str = ""
    true_score: float = 0.0
    # Archived vendor file path — surfaced after Step 11 for Step 15.
    _archived_vendor_file: Path | None = None

    log.info(
        "=== START execution=%s record=%s submission=%s site=%s vendor=%s ===",
        execution_id, record.record_id, record.submission_id,
        record.site_number, record.vendor_email,
    )

    try:
        # Step 1: Validate critical Airtable fields
        _validate_record(record)

        # Step 1.5: Ensure Submission ID is populated in Airtable.
        # Airtable forms can leave this blank; the pipeline must backfill it so
        # the primary label and downstream audit trail are never empty.
        airtable.patch_submission_id(record.record_id, record.submission_id)

        # Step 2: Consult memory before doing anything
        # P1-B: Eligibility gate — skip the full O(N) archive scan if the
        # lesson library is empty (common on a fresh deployment).
        if memory.has_lessons():
            # P1-A: Dynamic tags from the record instead of hardcoded strings.
            mem_context = memory.recall(
                tags=[record.vendor_name.lower(), record.site_number, "file_parse"],
                query=f"site {record.site_number} vendor {record.vendor_name}",
            )
            if mem_context["rules"]:
                log.info("Memory context: %s", mem_context["summary"])
        else:
            log.debug("Memory: lesson archive empty — skipping recall.")
            mem_context: dict = {"lessons": [], "failures": [], "rules": [], "summary": ""}

        # Step 3: Download attachment
        attachment_path = airtable.download_attachment(record)

        # Step 4: Normalise file, overwrite Project ID, collect schema metadata
        load_result = load_vendor_file_with_metadata(attachment_path, record.site_number)
        df = load_result.dataframe
        rows_loaded = len(df)
        if df.empty:
            raise ValueError("Vendor file produced zero rows after normalisation.")

        validation = validate_submission_for_site(
            cfg=cfg,
            site_number=record.site_number,
            load_result=load_result,
            survey_type=record.survey_type,
        )

        error_df = None
        should_run_python = validation.is_valid_for_grading
        if not should_run_python:
            error_message = "Site-indexed validation failed: " + ", ".join(validation.reason_codes)
            notes_internal = (
                f"SubmissionID={record.submission_id} | Site={record.site_number}\n"
                f"Validation failed before grading.\n"
                f"Reason codes: {', '.join(validation.reason_codes)}\n"
                f"Missing critical cols: {validation.missing_critical_columns or 'none'}\n"
                f"Reference rows: {validation.reference_row_count} | "
                f"Submitted rows: {validation.normalized_row_count}"
            )
            true_score = 0.0
            result = SubmissionResult(
                submission_id=record.submission_id,
                status=ProcessingStatus.FAIL,
                score=0.0,
                message=error_message,
            )
        else:
            try:
                grade_outcome = grade_submission_in_python(
                    cfg=cfg,
                    submission_df=df,
                    submission_id=record.submission_id,
                    site_number=record.site_number,
                    survey_type=record.survey_type,
                )
                result = grade_outcome.result
                error_df = grade_outcome.error_df
                # True Score is always the raw numeric value from the grader.
                true_score = float(result.score) if result.score is not None else 0.0
                notes_internal = grade_outcome.notes_internal or ""
            except Exception as exc:  # noqa: BLE001
                error_message = str(exc)
                log.exception(
                    "Python grading failure: execution=%s submission=%s | %s",
                    execution_id, record.submission_id, exc,
                )
                notes_internal = (
                    f"SubmissionID={record.submission_id} | Site={record.site_number}\n"
                    f"Python grader raised an exception.\n"
                    f"Error: {error_message[:1000]}"
                )
                true_score = 0.0
                result = SubmissionResult(
                    submission_id=record.submission_id,
                    status=ProcessingStatus.FAIL,
                    score=0.0,
                    message=error_message,
                )

        # RULE: status is ALWAYS re-derived from true_score after grading.
        # Never trust result.status alone — it may reflect a different reference
        # dataset (e.g. before the SQL DB was cleaned). status_from_score() is
        # the single source of truth. This prevents stale FAIL from persisting.
        final_status = status_from_score(true_score)
        validate_grading_consistency(
            true_score=true_score,
            status=final_status,
            context=f"execution={execution_id} submission={record.submission_id}",
        )

        score = result.score
        error_count = len(error_df) if error_df is not None else 0
        error_message = result.message

        # Step 9: Airtable automation handles vendor email — no action needed here.
        # The status written in Step 10 triggers the Airtable automation rule.
        output_report_path = ""

        # Step 10: Write Processing Status + Score + Fail Summary to Airtable.
        #
        # Canonical writeback rules:
        #   • True Score  — ALWAYS the raw numeric value, never blank.
        #   • Score field — ALWAYS the numeric % derived from True Score (e.g. '95.6%').
        #                   PASS and FAIL both write a numeric %. Status field carries PASS/FAIL.
        #   • Status      — ALWAYS derived from true_score via status_from_score().
        #   • Notes       — ALWAYS populated; never blank after processing.
        if not notes_internal.strip():
            notes_internal = (
                f"SubmissionID={record.submission_id} | Site={record.site_number}\n"
                f"Auto-generated pipeline diagnostics.\n"
                f"Status={final_status.value} | TrueScore={true_score}"
            )

        airtable_status = (
            STATUS_PASS if final_status == ProcessingStatus.PASS
            else STATUS_FAIL
        )
        fail_summary = _build_fail_summary(result, error_df)

        airtable.update_result(
            record_id=record.record_id,
            status=airtable_status,
            score=true_score,        # always numeric — never None
            fail_summary=fail_summary,
            notes_internal=notes_internal,
            true_score=true_score,
        )

    except Exception as exc:  # noqa: BLE001
        error_message = str(exc)
        log.exception(
            "Pipeline failure: execution=%s submission=%s | %s",
            execution_id, record.submission_id, exc,
        )
        # Business rule: no ERRORs. Pipeline exception = FAIL with score 0.
        # Always write ALL fields so Airtable never shows blanks.
        _handle_failure(airtable, cfg, record, error_message)
        final_status = ProcessingStatus.FAIL
        score = 0.0
        true_score = 0.0
        notes_internal = (
            f"SubmissionID={record.submission_id} | Site={record.site_number}\n"
            f"Pipeline exception before grading completed.\n"
            f"Error: {error_message[:1000]}"
        )
        error_count = 0

    finally:
        duration = time.monotonic() - start_time
        processed_at = datetime.now(timezone.utc).isoformat()

        # Canonical score for archiving: true_score is ALWAYS a float (0.0 default).
        # raw `score` from result.score can be None if grading never ran (network/crash).
        # Use true_score as the fallback so archives never contain None.
        canonical_score: float = score if score is not None else true_score

        # Step 11: Archive submission (copy raw file BEFORE temp delete)
        sub_archive = SubmissionArchiveRecord(
            record_id=record.record_id,
            submission_id=record.submission_id,
            vendor_email=record.vendor_email,
            vendor_name=record.vendor_name,
            site_number=record.site_number,
            attachment_filename=record.attachment_filename,
            archived_file_path="",  # filled by save_submission_archive
            submitted_at=record.submitted_at or processed_at,
            processed_at=processed_at,
            status=final_status.value,
            score=canonical_score,
            error_count=error_count,
            output_report_path=output_report_path,
            sql_project_key=record.site_number,
            execution_id=execution_id,
            notes=error_message[:500],
            team_key=record.team_key,
        )
        try:
            archive_result = archive.save_submission_archive(sub_archive, attachment_path)
            _archived_vendor_file = archive_result.archived_file_path
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to archive submission metadata: %s", exc)
            _archived_vendor_file = None

        # Clean up temp file AFTER archiving the raw file
        safe_delete(attachment_path)

        # Step 12: Internal reviewer
        # P1-C: Wire memory warnings into the reviewer via extra_context.
        # surface_warnings_for_review() was defined but never called — fixed.
        memory_warnings = memory.surface_warnings_for_review() if memory.has_lessons() else []
        review = review_pipeline_run(
            submission_id=record.submission_id,
            site_number=record.site_number,
            rows_loaded=rows_loaded,
            status=final_status.value,
            score=canonical_score,
            error_message=error_message,
            extra_context={"memory_warnings": memory_warnings} if memory_warnings else None,
        )

        # Step 13: Archive execution + review
        exec_record = ExecutionRecord(
            execution_id=execution_id,
            submission_id=record.submission_id,
            record_id=record.record_id,
            vendor_email=record.vendor_email,
            site_number=record.site_number,
            status=final_status,
            score=canonical_score,
            error_message=error_message,
            rows_loaded=rows_loaded,
            duration_seconds=duration,
            team_key=record.team_key,
        )
        archive.save_execution(exec_record)
        archive.save_review(execution_id, review)

        # Step 14: Extract lesson on failure
        if final_status in (ProcessingStatus.FAIL, ProcessingStatus.ERROR):
            _maybe_extract_lesson(archive, exec_record, review)

        # ------------------------------------------------------------------
        # Step 15: Post-pass correction (downstream only — after all grading,
        #          pass/fail determination, and Airtable posting are complete).
        #
        #   • Grade identifier: true_score — the exact numeric value already
        #     written to the Airtable "True Score" column by the grader.
        #     This module reads it; it does not recompute or modify it.
        #   • Trigger: true_score >= 95.0 only. Silent no-op below threshold.
        #   • Never re-grades. Never changes pass/fail. Never changes score.
        #   • Never writes back to Airtable.
        #   • Outputs three files labeled {site_number}_{vendor_name}:
        #       RAW      — untouched copy of original vendor file
        #       CORRECTED— corrected CSV in original submission schema
        #       LOG      — correction log (primary audit artifact)
        # ------------------------------------------------------------------
        if (
            final_status == ProcessingStatus.PASS
            and _archived_vendor_file is not None
            and should_run_post_pass_correction(record.survey_type)
        ):
            # Guard: CorrectionWorker may have already processed this record
            # between the time grading started and Step 15 runs. Skip if so.
            _already_done = (
                correction_state is not None
                and correction_state.is_corrected(record.record_id)
            )
            if _already_done:
                log.info(
                    "Step 15 skipped: record=%s already corrected by CorrectionWorker.",
                    record.record_id,
                )
            else:
                correction_summary = run_post_pass_correction(
                    cfg=cfg,
                    submission_id=record.submission_id,
                    site_number=record.site_number,
                    vendor_name=record.vendor_name,
                    true_score=true_score,
                    archived_file_path=_archived_vendor_file,
                )
                if correction_summary is not None:
                    log.info(
                        "Step 15 complete: submission=%s site=%s vendor=%s "
                        "true_score=%.4f corrections=%d rows_touched=%d "
                        "review_flags=%d",
                        record.submission_id,
                        record.site_number,
                        record.vendor_name,
                        true_score,
                        correction_summary.total_corrections,
                        correction_summary.total_rows_touched,
                        correction_summary.total_review_flags,
                    )
                    # Mark corrected so CorrectionWorker won't re-run it
                    if correction_state is not None:
                        correction_state.mark_corrected(
                            record.record_id,
                            submission_id=record.submission_id,
                            site_number=record.site_number,
                            vendor_name=record.vendor_name,
                            true_score=true_score,
                            corrected_csv_path=correction_summary.corrected_csv_path,
                            correction_log_path=correction_summary.correction_log_path,
                        )

        log.info(
            "=== END execution=%s status=%s score=%s true_score=%s rows=%d duration=%.2fs ===",
            execution_id, final_status.value, canonical_score, true_score, rows_loaded, duration,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalized_score_for_reporting(
    status: ProcessingStatus,
    score: float | None,
) -> float | None:
    """Return a dashboard-friendly numeric score.

    Business rule:
    - PASS should contribute 100.0 to reporting averages.
    - FAIL should keep its Python-computed numeric score.
    - ERROR should not contribute to score averages.

    Airtable still receives the literal string 'PASS' for successful runs,
    but the archive/metrics layer should store a consistent numeric value so
    dashboards do not randomly exclude PASS submissions from averages.
    """
    if status == ProcessingStatus.PASS:
        return 100.0
    if status == ProcessingStatus.FAIL:
        return score
    return None


def _summarize_fail_issues(error_df: "pd.DataFrame | None") -> list[str]:
    """Return concise human-readable issue lines for FAIL summaries/notes."""
    if error_df is None or error_df.empty:
        return []

    issue_type_col = "IssueType" if "IssueType" in error_df.columns else None
    detail_col = "Detail" if "Detail" in error_df.columns else None
    lines: list[str] = []

    if issue_type_col and detail_col:
        counts = (
            error_df[issue_type_col]
            .fillna("<blank>")
            .astype(str)
            .value_counts()
        )
        summary = ", ".join(
            f"{issue_type}={count}"
            for issue_type, count in counts.items()
        )
        if summary:
            lines.append(f"Issue counts: {summary}")

        for _, row in error_df.head(10).iterrows():
            issue_type = str(row.get(issue_type_col, "")).strip() or "ISSUE"
            detail = str(row.get(detail_col, "")).strip()
            lines.append(f"  - [{issue_type}] {detail}" if detail else f"  - [{issue_type}]")
        if len(error_df) > 10:
            lines.append(f"  ... and {len(error_df) - 10} more rows")
        return lines

    for _, row in error_df.head(10).iterrows():
        parts = []
        for col in error_df.columns:
            val = row.get(col, "")
            if val and str(val).strip():
                parts.append(f"{col}={val}")
        if parts:
            lines.append("  - " + " | ".join(parts))
    if len(error_df) > 10:
        lines.append(f"  ... and {len(error_df) - 10} more rows")
    return lines



def _build_fail_summary(
    result,           # SubmissionResult
    error_df: "pd.DataFrame | None",
) -> str:
    """Build a concise Fail Summary string for the Airtable field."""
    if result.status == ProcessingStatus.PASS:
        return ""

    if result.status == ProcessingStatus.ERROR:
        msg = result.message if hasattr(result, "message") and result.message else ""
        return f"Processing Error: {msg}" if msg else "Processing Error (see pipeline logs)"

    score_str = f"{result.score:.1f}%" if result.score is not None else "N/A"
    lines = [f"Score: {score_str}", ""]
    issue_lines = _summarize_fail_issues(error_df)

    if issue_lines:
        lines.append("Issues found:")
        lines.extend(issue_lines)
    elif hasattr(result, "message") and result.message:
        lines.append(result.message)

    return "\n".join(lines)


def _validate_record(record: AirtableRecord) -> None:
    """Raise ValueError with a clear message if critical fields are blank."""
    if not record.vendor_email:
        raise ValueError(
            f"Record {record.record_id} is missing Vendor Email. Cannot send result."
        )
    if not record.site_number:
        raise ValueError(
            f"Record {record.record_id} is missing Site Number. "
            "Project ID cannot be overwritten. Rejecting submission."
        )
    if not record.attachment_url:
        raise ValueError(
            f"Record {record.record_id} has no attachment. No file to process."
        )


def _handle_failure(
    airtable: AirtableClient,
    cfg: AppConfig,
    record: AirtableRecord,
    error_message: str,
) -> None:
    """On pipeline exception: write FAIL to Airtable with all required fields populated.

    EVERY field must always be written. Blank fields in Airtable are a bug.
    """
    failure_notes = (
        f"SubmissionID={record.submission_id} | Site={record.site_number}\n"
        f"Pipeline exception — grading could not complete.\n"
        f"Error: {error_message[:1000]}"
    )
    fail_summary = f"Processing error: {error_message[:500]}"
    try:
        airtable.update_result(
            record_id=record.record_id,
            status=STATUS_FAIL,
            score=0.0,
            fail_summary=fail_summary,
            notes_internal=failure_notes,
            true_score=0.0,
        )
    except Exception as exc:  # noqa: BLE001
        log.error(
            "Failed to write verified FAIL result for record %s: %s — "
            "trying status-only as absolute last resort.",
            record.record_id, exc,
        )
        try:
            airtable.update_status(record.record_id, STATUS_FAIL)
        except Exception as exc2:  # noqa: BLE001
            log.error(
                "Failed even status-only write for record %s: %s",
                record.record_id, exc2,
            )
    if record.vendor_email:
        log.info(
            "Airtable automation will handle ERROR notification for submission=%s.",
            record.submission_id,
        )


def _maybe_extract_lesson(
    archive: Archive,
    exec_record: ExecutionRecord,
    review,  # ReviewResult
) -> None:
    """Extract a lesson from the failure if review surfaced actionable issues."""
    high_issues = [
        i for i in review.issues
        if i.severity.value in ("HIGH", "CRITICAL")
        and i.issue_type != "Concurrency"  # already in known patterns
    ]
    if not high_issues:
        return

    issue = high_issues[0]
    try:
        extract_lesson_from_failure(
            archive=archive,
            execution_id=exec_record.execution_id,
            task_category=_categorise(issue.issue_type),
            failed_pattern=issue.detail[:300],
            root_cause=f"Detected during review of {exec_record.execution_id}",
            fix_pattern=(
                review.recommended_fixes[0]
                if review.recommended_fixes
                else "See review output for recommendations."
            ),
            generalized_rule=(
                f"Avoid '{issue.issue_type}' class issues: {issue.detail[:150]}"
            ),
            tags=[_categorise(issue.issue_type), issue.issue_type.lower()],
            confidence=0.75,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not extract lesson: %s", exc)


def _categorise(issue_type: str) -> str:
    """Map review issue type to a task category string for lesson tagging."""
    mapping = {
        "Concurrency": "sql_import",
        "BusinessRule": "business_rules",
        "DataLoad": "sql_import",
        "DataQuality": "data_quality",
        "ErrorHandling": "reliability",
        "SecretsExposure": "security",
        "ConfigCentralization": "config",
        "Logging": "observability",
        "Maintainability": "code_quality",
        "Reliability": "reliability",
    }
    return mapping.get(issue_type, "general")
