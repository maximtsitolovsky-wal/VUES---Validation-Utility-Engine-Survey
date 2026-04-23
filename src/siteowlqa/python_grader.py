"""Python-first site-scoped grading logic for SiteOwlQA.

Design:
- Site Number scopes the reference dataset fetched from SQL.
- Only comparable canonical vendor columns are used.
- Submission rows and reference rows are normalized and sorted deterministically.
- Comparison is row-parallel within the site-scoped dataset.
- Result semantics:
    * PASS  -> raw numeric true score >= 95.0
    * FAIL  -> raw numeric true score < 95.0
    * ERROR -> true processing/comparison failure only
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

import pandas as pd

from siteowlqa.config import (
    PASS_THRESHOLD,
    VENDOR_GRADE_COLUMNS,
    SURVEY_TYPE_FA_INTRUSION,
    FA_INTRUSION_NAME_CONDITION_COLUMN,
    get_grade_columns_for_survey_type,
)
from siteowlqa.models import ProcessingStatus, SubmissionResult
from siteowlqa.reference_data import fetch_reference_rows

log = logging.getLogger(__name__)

# Default comparable columns (for BOTH or unspecified survey type)
COMPARABLE_COLUMNS: tuple[str, ...] = VENDOR_GRADE_COLUMNS

# Identity key for pairing submission rows to reference rows.
# Subset grading needs a stable unique key. MAC is best; IP is a good backup.
IDENTITY_COLUMNS: tuple[str, ...] = (
    "MAC Address",
    "IP Address",
)

SORT_COLUMNS: tuple[str, ...] = COMPARABLE_COLUMNS
PASS_THRESHOLD_DECIMAL = Decimal(str(PASS_THRESHOLD))


# ---------------------------------------------------------------------------
# Grading integrity — single source of truth for score → status mapping
# ---------------------------------------------------------------------------

class GradingInconsistencyError(Exception):
    """Raised when a computed score and an assigned status are contradictory.

    Example: true_score=95.6 but status=FAIL is a data integrity violation,
    not a display bug. Treat every instance as a pipeline bug to be fixed.
    """


def status_from_score(true_score: float) -> ProcessingStatus:
    """Single source of truth: derive PASS or FAIL from a numeric score.

    Rule:
        true_score >= PASS_THRESHOLD  →  ProcessingStatus.PASS   (always)
        true_score <  PASS_THRESHOLD  →  ProcessingStatus.FAIL

    Uses Decimal(str(...)) internally for float stability so that values like
    95.0000000000001 and 95.00 are both reliably PASS.

    Call this function everywhere status needs to be determined.  Never derive
    status through any other path.
    """
    if Decimal(str(true_score)) >= PASS_THRESHOLD_DECIMAL:
        return ProcessingStatus.PASS
    return ProcessingStatus.FAIL


def validate_grading_consistency(
    true_score: float,
    status: ProcessingStatus,
    context: str = "",
) -> None:
    """Assert that *status* is consistent with *true_score*.

    Integrity rule is strictly based on raw true_score:
        status_from_score(true_score) must equal status.

    Display rounding (e.g. 94.95 -> shown as 95.0%) is presentation only and
    must never trigger pipeline exceptions or score resets.
    """
    ctx = f" [{context}]" if context else ""
    expected = status_from_score(true_score)

    if expected != status:
        msg = (
            f"GRADING_INCONSISTENCY{ctx}: true_score={true_score} "
            f"→ expected status={expected.value} but got status={status.value}. "
            f"Score >= {PASS_THRESHOLD}% MUST be {ProcessingStatus.PASS.value}."
        )
        log.error("GRADING_INCONSISTENCY | %s", msg)
        raise GradingInconsistencyError(msg)


@dataclass(frozen=True)
class PythonGradeOutcome:
    result: SubmissionResult
    error_df: pd.DataFrame | None
    reference_row_count: int
    submission_row_count: int
    notes_internal: str = ""
    accuracy_pct: float | None = None
    coverage_pct: float | None = None


def grade_submission_in_python(
    *,
    cfg,
    submission_df: pd.DataFrame,
    submission_id: str,
    site_number: str,
    survey_type: str | None = None,
) -> PythonGradeOutcome:
    """Grade a submission against reference data.
    
    Args:
        cfg: Application configuration.
        submission_df: The vendor submission DataFrame.
        submission_id: Unique submission identifier.
        site_number: Site/Project number for reference lookup.
        survey_type: One of 'CCTV', 'FA/Intrusion', 'BOTH', or None.
                     Determines which columns are graded.
                     None defaults to 'BOTH' for backward compatibility.
    """
    # Get the grading columns for this survey type
    grade_columns = get_grade_columns_for_survey_type(survey_type)
    
    reference_df = fetch_reference_rows(cfg, site_number)
    if reference_df.empty:
        # Business rule: no ERRORs. Missing reference is a FAIL with score 0.
        return _fail(
            submission_id=submission_id,
            message=f"SITE_REFERENCE_NOT_FOUND: ProjectID={site_number}",
            submission_row_count=len(submission_df),
            reference_row_count=0,
        )

    submission_norm = _normalize_for_compare(submission_df, site_number, grade_columns, survey_type)
    reference_norm = _normalize_for_compare(reference_df, site_number, grade_columns, survey_type)

    # Filter rows based on survey type to avoid overlap:
    # - CCTV: only rows where Abbreviated Name AND Description are empty (camera rows)
    # - FA/Intrusion: only rows where Abbreviated Name OR Description have content (panel rows)
    # - BOTH: all rows
    submission_filtered = _filter_rows_by_survey_type(submission_norm, survey_type)
    reference_filtered = _filter_rows_by_survey_type(reference_norm, survey_type)
    
    log.info(
        "ROW_FILTER | survey_type=%s | submission: %d -> %d | reference: %d -> %d",
        survey_type, len(submission_norm), len(submission_filtered),
        len(reference_norm), len(reference_filtered),
    )

    # Use survey-type-specific columns, filtered to those present in reference
    comparable_cols = _select_comparable_columns(reference_filtered, grade_columns)
    
    # FA/Intrusion special case: include "Name" only if Abbreviated Name has content
    if survey_type == SURVEY_TYPE_FA_INTRUSION:
        comparable_cols = _adjust_fa_intrusion_columns(comparable_cols, submission_filtered)

    if submission_filtered.empty:
        # Business rule: no ERRORs. Treat as FAIL with score 0.
        return _fail(
            submission_id=submission_id,
            message=f"NO_{survey_type or 'COMPARABLE'}_ROWS_AFTER_FILTERING",
            submission_row_count=0,
            reference_row_count=len(reference_filtered),
        )

    comparison = _compare_rows(submission_id, site_number, submission_filtered, reference_filtered, comparable_cols)
    error_df = comparison.error_df
    mismatch_count = len(error_df)

    # Scoring model (0-100): correct matches vs. total reference inventory.
    # This naturally penalizes both:
    # - Inaccurate submissions (mismatches reduce matched_rows)
    # - Incomplete submissions (missing inventory reduces score)
    # 
    # Use FILTERED row counts - we only score rows relevant to this survey type
    submitted_rows = max(len(submission_filtered), 1)
    reference_rows = max(len(reference_filtered), 1)

    accuracy = comparison.matched_rows / submitted_rows
    coverage = comparison.covered_reference_rows / reference_rows
    
    # Score = (correct matches / total reference rows) * 100
    # Example:
    #   - 100 reference items, 66 submitted & matched → score = 66.0
    #   - 100 reference items, 100 submitted but 33 matched → score = 33.0
    #   - 100 reference items, 100 submitted & matched → score = 100.0
    #
    # Keep the raw numeric score for grading + metric reporting.
    # Round only to stabilize binary floating noise, not to alter threshold semantics.
    raw_score = 100.0 * (comparison.matched_rows / reference_rows)
    score = round(raw_score, 10)
    accuracy_pct = round(100.0 * accuracy, 2)
    coverage_pct = round(100.0 * coverage, 2)

    notes_internal = _build_internal_notes(
        submission_id=submission_id,
        site_number=site_number,
        submission_row_count=len(submission_filtered),
        reference_row_count=len(reference_filtered),
        accuracy_pct=accuracy_pct,
        coverage_pct=coverage_pct,
        comparable_cols=comparable_cols,
        missing_canonical_cols=_missing_columns_in_raw(submission_df),
    )

    # PASS/FAIL is derived ONLY via status_from_score() — the single source of truth.
    # status_from_score() uses Decimal comparison internally for float stability.
    # One call, one return path, no branching on score twice.
    status = status_from_score(score)
    result = SubmissionResult(
        submission_id=submission_id,
        status=status,
        score=score,
        message=(
            ""
            if status == ProcessingStatus.PASS
            else _build_fail_message(error_df, len(submission_filtered), len(reference_filtered))
        ),
    )
    return PythonGradeOutcome(
        result=result,
        error_df=None if status == ProcessingStatus.PASS else error_df,
        reference_row_count=len(reference_filtered),
        submission_row_count=len(submission_filtered),
        notes_internal=notes_internal,
        accuracy_pct=accuracy_pct,
        coverage_pct=coverage_pct,
    )


def _normalize_for_compare(
    df: pd.DataFrame,
    site_number: str,
    grade_columns: tuple[str, ...] | None = None,
    survey_type: str | None = None,
) -> pd.DataFrame:
    """Normalize a DataFrame for comparison.
    
    Args:
        df: Input DataFrame.
        site_number: Site number (for logging).
        grade_columns: Columns to grade. Defaults to VENDOR_GRADE_COLUMNS.
        survey_type: Survey type for special handling.
    """
    if grade_columns is None:
        grade_columns = VENDOR_GRADE_COLUMNS
    
    # Always include all possible columns for normalization,
    # but we'll only compare the grade_columns
    all_cols = VENDOR_GRADE_COLUMNS
    
    work = df.copy()
    # Only grade on the comparable columns. Ignore everything else.
    for col in all_cols:
        if col not in work.columns:
            work[col] = ""

    work = work[list(all_cols)].fillna("").astype(str)
    for col in all_cols:
        work[col] = work[col].map(_canon)

    work = work.sort_values(list(SORT_COLUMNS), kind="mergesort").reset_index(drop=True)
    return work


def _adjust_fa_intrusion_columns(
    comparable_cols: tuple[str, ...],
    submission_df: pd.DataFrame,
) -> tuple[str, ...]:
    """For FA/Intrusion surveys, only include 'Name' if 'Abbreviated Name' has content.
    
    Business rule: FA/Intrusion grades 'Name' only if there is content in the
    Abbreviated Name field. Otherwise, 'Name' is excluded from grading.
    """
    # Check if Abbreviated Name column has any non-empty content
    abbrev_col = FA_INTRUSION_NAME_CONDITION_COLUMN
    has_abbreviated_content = False
    
    if abbrev_col in submission_df.columns:
        # Check if any row has content in Abbreviated Name
        abbrev_values = submission_df[abbrev_col].fillna("").astype(str)
        has_abbreviated_content = abbrev_values.str.strip().ne("").any()
    
    if has_abbreviated_content:
        # Include "Name" in grading
        if "Name" not in comparable_cols:
            return ("Name",) + comparable_cols
        return comparable_cols
    else:
        # Exclude "Name" from grading
        return tuple(col for col in comparable_cols if col != "Name")


@dataclass(frozen=True)
class ComparisonResult:
    matched_rows: int
    covered_reference_rows: int
    error_df: pd.DataFrame


def _compare_rows(
    submission_id: str,
    site_number: str,
    submission_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    comparable_cols: tuple[str, ...],
) -> ComparisonResult:
    issue_rows: list[dict[str, str]] = []
    exact_pairs, submission_left, reference_left = _pair_exact_matches(submission_df, reference_df)
    matched_rows = exact_pairs
    covered_reference_rows = exact_pairs

    aligned_pairs, submission_unmatched, reference_unmatched = _pair_identity_matches(
        submission_left,
        reference_left,
    )
    for row_number, sub, ref in aligned_pairs:
        covered_reference_rows += 1
        mismatched_cols: list[str] = []
        for col in comparable_cols:
            ref_val = str(ref[col])
            sub_val = str(sub[col])

            # Giant-VLOOKUP semantics:
            # - If the submission doesn't provide a value, don't penalize.
            # - If the reference doesn't provide a value for optional fields, don't penalize.
            if not sub_val.strip() or sub_val.strip() == "0":
                continue

            if col in {"Abbreviated Name", "Description"}:
                if not ref_val.strip() or ref_val.strip() == "0":
                    continue

            if ref_val != sub_val:
                mismatched_cols.append(col)
        if mismatched_cols:
            issue_rows.append(
                {
                    "SubmissionID": submission_id,
                    "ProjectID": site_number,
                    "IssueType": "ROW_MISMATCH",
                    "Detail": _format_row_detail(row_number, mismatched_cols, ref, sub),
                }
            )
        else:
            matched_rows += 1

    # Subset grading: row-count mismatch is expected and not an issue.

    issue_rows.extend(
        _build_unmatched_issue_rows(submission_id, site_number, "EXTRA_ROW", submission_unmatched)
    )

    # Subset grading: missing rows in the submission are NOT an error.
    # (Vendor may submit only cameras, only new installs, etc.)

    return ComparisonResult(
        matched_rows=matched_rows,
        covered_reference_rows=covered_reference_rows,
        error_df=pd.DataFrame(
            issue_rows,
            columns=["SubmissionID", "ProjectID", "IssueType", "Detail"],
        ),
    )


def _format_row_detail(
    row_number: int,
    mismatched_cols: list[str],
    ref: pd.Series,
    sub: pd.Series,
) -> str:
    parts = [f"Row {row_number}"]
    for col in mismatched_cols[:3]:
        parts.append(
            f"{col}: REF={_display(ref[col])} | SUB={_display(sub[col])}"
        )
    if len(mismatched_cols) > 3:
        parts.append(f"... {len(mismatched_cols) - 3} more differing fields")
    return " | ".join(parts)


def _build_fail_message(
    error_df: pd.DataFrame,
    submission_rows: int,
    reference_rows: int,
) -> str:
    if error_df.empty:
        return (
            f"Submission data did not match the site reference "
            f"(submission={submission_rows}, reference={reference_rows})."
        )

    counts = error_df["IssueType"].value_counts().to_dict()
    fragments = [f"{issue_type}={count}" for issue_type, count in counts.items()]
    return (
        f"Submission data did not match the site reference "
        f"(submission={submission_rows}, reference={reference_rows}; "
        f"{' , '.join(fragments)})."
    )


def _pair_exact_matches(
    submission_df: pd.DataFrame,
    reference_df: pd.DataFrame,
) -> tuple[int, list[pd.Series], list[pd.Series]]:
    ref_buckets: dict[tuple[str, ...], list[pd.Series]] = defaultdict(list)
    for _, row in reference_df.iterrows():
        ref_buckets[_full_fingerprint(row)].append(row)

    matched = 0
    submission_left: list[pd.Series] = []
    for _, row in submission_df.iterrows():
        key = _full_fingerprint(row)
        bucket = ref_buckets.get(key)
        if bucket:
            bucket.pop()
            matched += 1
        else:
            submission_left.append(row)

    reference_left: list[pd.Series] = []
    for bucket in ref_buckets.values():
        reference_left.extend(bucket)
    return matched, submission_left, reference_left


def _pair_identity_matches(
    submission_rows: list[pd.Series],
    reference_rows: list[pd.Series],
) -> tuple[list[tuple[int, pd.Series, pd.Series]], list[pd.Series], list[pd.Series]]:
    ref_buckets: dict[tuple[str, ...], list[pd.Series]] = defaultdict(list)
    for row in reference_rows:
        ref_buckets[_identity_fingerprint(row)].append(row)

    aligned_pairs: list[tuple[int, pd.Series, pd.Series]] = []
    submission_unmatched: list[pd.Series] = []
    row_number = 1
    for row in submission_rows:
        key = _identity_fingerprint(row)
        bucket = ref_buckets.get(key)
        if bucket:
            ref_row = bucket.pop(0)
            aligned_pairs.append((row_number, row, ref_row))
            row_number += 1
        else:
            submission_unmatched.append(row)

    reference_unmatched: list[pd.Series] = []
    for bucket in ref_buckets.values():
        reference_unmatched.extend(bucket)
    return aligned_pairs, submission_unmatched, reference_unmatched


def _build_unmatched_issue_rows(
    submission_id: str,
    site_number: str,
    issue_type: str,
    rows: list[pd.Series],
) -> list[dict[str, str]]:
    issue_rows: list[dict[str, str]] = []
    for idx, row in enumerate(rows[:10], start=1):
        issue_rows.append(
            {
                "SubmissionID": submission_id,
                "ProjectID": site_number,
                "IssueType": issue_type,
                "Detail": f"{issue_type} {idx}: {_row_signature_text(row)}",
            }
        )
    if len(rows) > 10:
        issue_rows.append(
            {
                "SubmissionID": submission_id,
                "ProjectID": site_number,
                "IssueType": issue_type,
                "Detail": f"{issue_type}: ... and {len(rows) - 10} more rows",
            }
        )
    return issue_rows


def _full_fingerprint(row: pd.Series) -> tuple[str, ...]:
    return tuple(str(row[col]) for col in COMPARABLE_COLUMNS)


def _select_comparable_columns(
    reference_df: pd.DataFrame,
    grade_columns: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    """Pick which columns to compare based on survey type and reference content.

    Args:
        reference_df: Reference DataFrame.
        grade_columns: Columns to grade for this survey type. If None, uses default.
    
    Optional fields (Abbreviated Name, Description) are only compared if the
    reference has them populated for this site.
    """
    if grade_columns is None:
        # Default behavior for backward compatibility
        base = [
            "Name",
            "Part Number",
            "Manufacturer",
            "IP Address",
            "MAC Address",
            "IP / Analog",
        ]
    else:
        # Use survey-type-specific columns as base
        base = list(grade_columns)

    # For optional columns, only include if reference has content
    optional = []
    optional_cols = ["Abbreviated Name", "Description"]
    
    for opt_col in optional_cols:
        # Only add optional columns if they're in our grade_columns AND have content
        if grade_columns is not None and opt_col not in grade_columns:
            continue
        if opt_col in reference_df.columns:
            if reference_df[opt_col].astype(str).str.strip().replace("0", "").ne("").any():
                if opt_col not in base:
                    optional.append(opt_col)

    # Preserve canonical order
    ordered = [c for c in COMPARABLE_COLUMNS if c in (base + optional)]
    return tuple(ordered)


def _identity_fingerprint(row: pd.Series) -> tuple[str, ...]:
    return tuple(str(row[col]) for col in IDENTITY_COLUMNS)


def _row_signature_text(row: pd.Series) -> str:
    parts = []
    for col in IDENTITY_COLUMNS:
        value = _display(row[col])
        parts.append(f"{col}={value}")
    return " | ".join(parts)


def _canon(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.strip().upper()
    if text in {"", "0"}:
        return ""
    # Ignore special characters (spaces, underscores, punctuation, parentheses).
    # Compare only core alphanumeric text.
    return re.sub(r"[^A-Z0-9]+", "", text)


def _display(value: object) -> str:
    text = _canon(value)
    return text if text else "<blank>"


def _fail(
    *,
    submission_id: str,
    message: str,
    submission_row_count: int,
    reference_row_count: int,
) -> PythonGradeOutcome:
    return PythonGradeOutcome(
        result=SubmissionResult(
            submission_id=submission_id,
            status=ProcessingStatus.FAIL,
            score=0.0,
            message=message,
        ),
        error_df=None,
        reference_row_count=reference_row_count,
        submission_row_count=submission_row_count,
        notes_internal=message,
        accuracy_pct=None,
        coverage_pct=None,
    )


def _missing_columns_in_raw(raw_df: pd.DataFrame) -> list[str]:
    """Return which canonical grade columns are not present in raw upload.

    Note: This is based on the *raw* incoming dataframe (before normalization),
    so it reflects what the vendor actually provided.
    """
    raw_cols = {str(c).strip().lower() for c in raw_df.columns}
    missing = [c for c in VENDOR_GRADE_COLUMNS if c.strip().lower() not in raw_cols]
    return missing


def _build_internal_notes(
    *,
    submission_id: str,
    site_number: str,
    submission_row_count: int,
    reference_row_count: int,
    accuracy_pct: float,
    coverage_pct: float,
    comparable_cols: tuple[str, ...],
    missing_canonical_cols: list[str],
) -> str:
    """Internal-only diagnostics for Airtable ""Notes for Internal"" field."""
    missing_pct = max(0.0, round(100.0 - coverage_pct, 2))
    lines: list[str] = []
    lines.append(f"SubmissionID={submission_id} | Site={site_number}")
    lines.append(
        f"Rows: submitted={submission_row_count} | reference={reference_row_count}"
    )
    lines.append(
        f"Accuracy={accuracy_pct:.2f}% | Coverage={coverage_pct:.2f}% | Missing={missing_pct:.2f}%"
    )
    lines.append(f"Comparable columns used: {', '.join(comparable_cols)}")
    if missing_canonical_cols:
        lines.append("Missing canonical columns in raw upload:")
        for c in missing_canonical_cols:
            lines.append(f"  - {c}")
    return "\n".join(lines)[:5000]
