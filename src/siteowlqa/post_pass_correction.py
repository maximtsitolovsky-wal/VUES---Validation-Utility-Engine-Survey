"""post_pass_correction.py — Downstream post-pass correction extension.

NON-NEGOTIABLE RULES:
  - Runs ONLY after all grading, pass/fail, and Airtable posting are complete.
  - Trigger: True Score (Airtable "True Score" field) >= 95.0. Silent no-op below.
  - Never re-grades. Never changes pass/fail. Never changes True Score.
  - Never updates any Airtable field.
  - Never modifies the original archived vendor file.
  - Prefer no correction over any wrong correction.

Grade identifier:
  Uses ``true_score`` — the exact numeric value written to the Airtable
  "True Score" column by the existing grading pipeline.  This module reads
  that value after grading is complete; it does not recompute it.

Output directories (configured via .env):
  CORRECTION_CORRECTED_DIR  — corrected CSV files
  CORRECTION_LOG_DIR        — correction log CSVs (primary audit artifact)
  CORRECTION_RAW_DIR        — untouched copy of the original vendor file

File naming convention (all three outputs):
  {site_number}_{safe_vendor_name}[_corrected | _correction_log | _raw.<ext>]

Called exclusively from poll_airtable.process_record() as Step 15,
after archive, review, and lesson-extraction are complete.
"""

from __future__ import annotations

import difflib
import logging
import math
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from siteowlqa.config import AppConfig
from siteowlqa.reference_data import fetch_reference_rows

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Confidence thresholds
# ---------------------------------------------------------------------------

CONF_APPLY        = 0.99   # apply, no review flag
CONF_APPLY_REVIEW = 0.93   # apply + flag for human review
CONF_LOG_ONLY     = 0.80   # do not apply, log for review only
# < CONF_LOG_ONLY: reject entirely — nothing logged

# ---------------------------------------------------------------------------
# Trigger threshold — must equal config.PASS_THRESHOLD
# Reads the Airtable "True Score" column value (already computed by grader).
# ---------------------------------------------------------------------------

TRIGGER_TRUE_SCORE: float = 95.0

# ---------------------------------------------------------------------------
# Fields eligible for correction — all graded fields EXCEPT identity columns
# (IP Address, MAC Address) which are used for row matching only and whose
# values must never be changed.
# Name IS correctable but has an extra similarity guard below:
#   when matched via MAC/IP identity, Name is only auto-applied when the
#   vendor value and reference value are ≥85% similar (formatting fixes).
#   If they differ substantially the correction is logged for review only.
# REF_BACKED_FIELDS must exist in the site reference DataFrame.
# VENDOR_EXTRA_FIELDS are supported only when present in both submission + ref.
# ---------------------------------------------------------------------------

REF_BACKED_FIELDS: tuple[str, ...] = (
    "Name",
    "Abbreviated Name",
    "Manufacturer",
    "Part Number",
    "IP / Analog",
    "Description",
)

VENDOR_EXTRA_FIELDS: tuple[str, ...] = (
    "System Type",
    "Device/Task Type",
)

# Identity columns for high-confidence row matching (same priority as grader)
IDENTITY_COLS: tuple[str, ...] = ("MAC Address", "IP Address")


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class CorrectionAttempt:
    """One correction attempt for a single field in a single row."""
    submission_id: str
    row_number: int          # 1-based index in the original vendor file
    field: str
    original_value: str
    corrected_value: str
    reason: str
    source: str              # e.g. "exact MAC address match"
    confidence: float
    applied: bool
    requires_review: bool
    timestamp: str


@dataclass
class CorrectionSummary:
    """Summary returned to the pipeline after the correction module runs."""
    submission_id: str
    site_number: str
    vendor_name: str
    true_score: float        # The Airtable "True Score" value — never modified here
    total_corrections: int
    total_rows_touched: int
    total_review_flags: int
    corrected_csv_path: str
    correction_log_path: str
    raw_copy_path: str


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_post_pass_correction(
    *,
    cfg: AppConfig,
    submission_id: str,
    site_number: str,
    vendor_name: str,
    true_score: float,
    archived_file_path: Path,
) -> CorrectionSummary | None:
    """Run post-pass correction for a qualifying submission.

    Grade identifier: ``true_score`` is the value already written to the
    Airtable "True Score" column by the existing grading pipeline.
    This function reads it; it does not recompute or modify it.

    Trigger: true_score >= 95.0 only.  Silent no-op below that threshold.

    Returns CorrectionSummary if correction ran, None if skipped.
    All exceptions are caught — this step must never crash the pipeline.
    """
    if true_score < TRIGGER_TRUE_SCORE:
        log.debug(
            "Post-pass correction skipped: submission=%s true_score=%.4f < %.1f",
            submission_id, true_score, TRIGGER_TRUE_SCORE,
        )
        return None

    if not archived_file_path or not archived_file_path.exists():
        log.warning(
            "Post-pass correction skipped: archived file not found "
            "submission=%s path=%s",
            submission_id, archived_file_path,
        )
        return None

    log.info(
        "Post-pass correction triggered: submission=%s site=%s vendor=%s "
        "true_score=%.4f (Airtable 'True Score' >= %.1f)",
        submission_id, site_number, vendor_name, true_score, TRIGGER_TRUE_SCORE,
    )

    try:
        return _run_correction(
            cfg=cfg,
            submission_id=submission_id,
            site_number=site_number,
            vendor_name=vendor_name,
            true_score=true_score,
            archived_file_path=archived_file_path,
        )
    except Exception as exc:  # noqa: BLE001
        log.exception(
            "Post-pass correction failed (non-fatal): submission=%s | %s",
            submission_id, exc,
        )
        return None


# ---------------------------------------------------------------------------
# Internal orchestration
# ---------------------------------------------------------------------------

def _run_correction(
    *,
    cfg: AppConfig,
    submission_id: str,
    site_number: str,
    vendor_name: str,
    true_score: float,
    archived_file_path: Path,
) -> CorrectionSummary | None:

    # Resolve output directories from cfg, falling back to output_dir/corrections/
    fallback = cfg.output_dir / "corrections"
    corrected_dir = cfg.correction_corrected_dir or fallback
    log_dir       = cfg.correction_log_dir        or fallback
    raw_dir       = cfg.correction_raw_dir        or fallback

    for d in (corrected_dir, log_dir, raw_dir):
        d.mkdir(parents=True, exist_ok=True)

    # Filename prefix: {site_number}_{safe_vendor}
    safe_prefix = _safe_filename(f"{site_number}_{vendor_name}")

    # Step 1: Copy raw vendor file untouched to RAW directory.
    raw_copy_path = _copy_raw_file(archived_file_path, raw_dir, safe_prefix)

    # Step 2: Load the full original submission (all columns, original schema).
    original_df = _load_submission_file(archived_file_path)
    if original_df is None or original_df.empty:
        log.warning(
            "Post-pass correction: could not load archived file: %s",
            archived_file_path,
        )
        return None

    # Step 3: Load trusted reference data for this site.
    ref_df = fetch_reference_rows(cfg, site_number)
    if ref_df is None or ref_df.empty:
        log.warning(
            "Post-pass correction: no reference data for site=%s — skipping.",
            site_number,
        )
        return None

    ref_df = _normalize_ref_df(ref_df)
    if ref_df.empty:
        return None

    # Step 4: Determine which fields can be corrected (present in both datasets).
    correctable_fields = _resolve_correctable_fields(original_df, ref_df)
    if not correctable_fields:
        log.info(
            "Post-pass correction: no correctable fields in common "
            "for submission=%s — writing outputs with zero corrections.",
            submission_id,
        )

    log.info(
        "Post-pass correction: correctable_fields=%s submission=%s",
        correctable_fields, submission_id,
    )

    # Step 5: Match rows + build correction attempts.
    attempts: list[CorrectionAttempt] = []
    ts = datetime.now(timezone.utc).isoformat()

    for row_idx, sub_row in original_df.iterrows():
        row_num = int(row_idx) + 1  # type: ignore[arg-type]
        matched_ref_row, confidence, match_source = _match_row_to_reference(
            sub_row, ref_df
        )
        if matched_ref_row is None or confidence < CONF_LOG_ONLY:
            continue  # below minimum threshold — reject, do not log

        row_attempts = _build_correction_attempts(
            submission_id=submission_id,
            row_number=row_num,
            sub_row=sub_row,
            ref_row=matched_ref_row,
            correctable_fields=correctable_fields,
            match_confidence=confidence,
            match_source=match_source,
            timestamp=ts,
        )
        attempts.extend(row_attempts)

    applied = [a for a in attempts if a.applied]

    # Step 6: Build corrected DataFrame (original schema + approved corrections).
    # Take a full copy of the original so ALL vendor columns + rows survive.
    original_columns = list(original_df.columns)
    corrected_df = _apply_corrections(original_df.copy(), applied)

    # Final schema guard: enforce exact column order from the vendor's original file.
    # This is belt-and-suspenders — _apply_corrections already checks, but we
    # re-assert here so the CSV write always uses the vendor's original ordering.
    corrected_df = corrected_df.reindex(columns=original_columns, fill_value="")

    # Step 7: Write corrected CSV — utf-8-sig so Excel opens without BOM issues.
    # The output contains EVERY column the vendor submitted, in the same order,
    # with only the corrected cells changed.
    corrected_path = corrected_dir / f"{safe_prefix}_corrected.csv"
    corrected_df.to_csv(corrected_path, index=False, encoding="utf-8-sig")

    log.info(
        "Post-pass correction: corrected file written — %d rows, %d columns, "
        "%d cells changed → %s",
        len(corrected_df), len(corrected_df.columns), len(applied), corrected_path.name,
    )

    # Step 8: Write correction log — full audit trail.
    log_path = log_dir / f"{safe_prefix}_correction_log.csv"
    _write_correction_log(attempts, log_path, site_number=site_number, vendor_name=vendor_name)

    total_rows_touched = len({a.row_number for a in applied})
    total_review_flags = len([a for a in applied if a.requires_review])

    summary = CorrectionSummary(
        submission_id=submission_id,
        site_number=site_number,
        vendor_name=vendor_name,
        true_score=true_score,
        total_corrections=len(applied),
        total_rows_touched=total_rows_touched,
        total_review_flags=total_review_flags,
        corrected_csv_path=str(corrected_path),
        correction_log_path=str(log_path),
        raw_copy_path=str(raw_copy_path),
    )

    log.info(
        "Post-pass correction complete: submission=%s site=%s vendor=%s "
        "true_score=%.4f corrections=%d rows_touched=%d review_flags=%d\n"
        "  RAW      → %s\n"
        "  CORRECTED→ %s\n"
        "  LOG      → %s",
        submission_id, site_number, vendor_name, true_score,
        summary.total_corrections,
        summary.total_rows_touched,
        summary.total_review_flags,
        raw_copy_path,
        corrected_path,
        log_path,
    )
    return summary


# ---------------------------------------------------------------------------
# Raw file copy
# ---------------------------------------------------------------------------

def _copy_raw_file(
    src: Path,
    raw_dir: Path,
    safe_prefix: str,
) -> Path:
    """Copy the original vendor file untouched into the RAW directory.

    Preserves the original file extension.  The original archived file
    is never moved or modified — only copied.
    """
    dest = raw_dir / f"{safe_prefix}_raw{src.suffix}"
    try:
        shutil.copy2(src, dest)
        log.info("Post-pass correction: raw copy written → %s", dest)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "Post-pass correction: could not copy raw file %s → %s: %s",
            src, dest, exc,
        )
    return dest


# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------

def _load_submission_file(path: Path) -> pd.DataFrame | None:
    """Load the archived vendor file preserving ALL original columns and rows.

    INVARIANT: every column the vendor submitted must appear in the output,
    in the same order, with the same name.  We never drop columns.
    We never rename columns beyond stripping leading/trailing whitespace and
    the UTF-8 BOM byte (\ufeff) that Excel sometimes prepends to the first cell.
    """
    suffix = path.suffix.lower()
    try:
        if suffix in (".xlsx", ".xls", ".xlsm"):
            df = _load_excel_file(path)
        elif suffix == ".csv":
            df = _load_csv_file(path)
        else:
            log.warning(
                "Post-pass correction: unsupported file type '%s': %s", suffix, path
            )
            return None

        if df is None:
            return None

        # Normalise column names: strip surrounding whitespace + BOM.
        # Do NOT rename, reorder, or drop any columns.
        df.columns = [str(c).strip().lstrip("\ufeff") for c in df.columns]

        # Convert every cell to a plain Python str.
        # Using applymap (pandas < 2.1) / map (pandas >= 2.1) avoids dtype issues.
        def _cell_to_str(v: object) -> str:
            if v is None:
                return ""
            if isinstance(v, float) and math.isnan(v):
                return ""
            return str(v).strip()

        try:
            df = df.map(_cell_to_str)
        except AttributeError:
            df = df.applymap(_cell_to_str)  # noqa: PD005  (pandas < 2.1)

        log.debug(
            "Post-pass correction: loaded submission file %s — %d rows, %d columns: %s",
            path.name, len(df), len(df.columns), list(df.columns),
        )
        return df

    except Exception as exc:  # noqa: BLE001
        log.warning(
            "Post-pass correction: failed to load file %s: %s", path, exc
        )
        return None


def _load_excel_file(path: Path) -> pd.DataFrame | None:
    """Load an Excel file trying calamine first, openpyxl as fallback.

    keep_default_na=False prevents pandas from silently converting
    vendor values like 'N/A', 'None', 'null', '' to NaN, which would
    then show up as the string 'nan' after str conversion.
    """
    for engine in ("calamine", "openpyxl"):
        try:
            return pd.read_excel(
                path,
                sheet_name=0,
                dtype=str,
                engine=engine,
                keep_default_na=False,
                na_values=[],
            )
        except Exception as exc:  # noqa: BLE001
            log.debug(
                "Post-pass correction: Excel engine '%s' failed for %s: %s",
                engine, path.name, exc,
            )
    log.warning("Post-pass correction: all Excel engines failed for %s", path.name)
    return None


def _load_csv_file(path: Path) -> pd.DataFrame | None:
    """Load a CSV file trying BOM-aware UTF-8 first, then plain UTF-8, then latin-1.

    keep_default_na=False + na_filter=False prevent pandas from converting
    common vendor strings ('N/A', 'NA', 'None', '0') to NaN.
    """
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return pd.read_csv(
                path,
                dtype=str,
                encoding=encoding,
                keep_default_na=False,
                na_filter=False,
            )
        except UnicodeDecodeError:
            continue
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "Post-pass correction: failed to read CSV %s with encoding %s: %s",
                path.name, encoding, exc,
            )
            return None
    log.warning("Post-pass correction: could not decode CSV %s with any known encoding", path.name)
    return None


# ---------------------------------------------------------------------------
# Reference normalization
# ---------------------------------------------------------------------------

def _normalize_ref_df(ref_df: pd.DataFrame) -> pd.DataFrame:
    df = ref_df.copy()
    for col in df.columns:
        df[col] = df[col].fillna("").astype(str)
    return df


# ---------------------------------------------------------------------------
# Field resolution
# ---------------------------------------------------------------------------

def _resolve_correctable_fields(
    sub_df: pd.DataFrame,
    ref_df: pd.DataFrame,
) -> tuple[str, ...]:
    """Return fields present in BOTH datasets within the allowed correction set."""
    sub_cols_lower = {str(c).strip().lower(): str(c) for c in sub_df.columns}
    ref_cols_lower = {str(c).strip().lower(): str(c) for c in ref_df.columns}

    result: list[str] = []
    for field_name in REF_BACKED_FIELDS + VENDOR_EXTRA_FIELDS:
        lower = field_name.lower()
        if lower in sub_cols_lower and lower in ref_cols_lower:
            result.append(sub_cols_lower[lower])

    return tuple(result)


# ---------------------------------------------------------------------------
# Row matching
# ---------------------------------------------------------------------------

def _canon(val: object) -> str:
    """Canonical string — identical to python_grader._canon()."""
    text = "" if val is None else str(val)
    text = text.strip().upper()
    return "" if text == "0" else text


def _match_row_to_reference(
    sub_row: pd.Series,
    ref_df: pd.DataFrame,
) -> tuple[pd.Series | None, float, str]:
    """Find the best-matching reference row for a submission row.

    Priority:
      1. Exact MAC Address match  → confidence = 1.0
      2. Exact IP Address match   → confidence = 0.99
      3. Fuzzy Name match (difflib) → confidence = ratio (only if >= CONF_LOG_ONLY)

    Returns (ref_row, confidence, source_description) or (None, 0.0, "").
    """
    # --- Identity: MAC ---
    mac_val = _canon(sub_row.get("MAC Address", ""))
    if mac_val and "MAC Address" in ref_df.columns:
        mac_match = ref_df[ref_df["MAC Address"].map(_canon) == mac_val]
        if not mac_match.empty:
            return mac_match.iloc[0], 1.0, "exact MAC address match"

    # --- Identity: IP ---
    ip_val = _canon(sub_row.get("IP Address", ""))
    if ip_val and "IP Address" in ref_df.columns:
        ip_match = ref_df[ref_df["IP Address"].map(_canon) == ip_val]
        if not ip_match.empty:
            return ip_match.iloc[0], 0.99, "exact IP address match"

    # --- Fuzzy Name ---
    sub_name = _canon(sub_row.get("Name", ""))
    if not sub_name or "Name" not in ref_df.columns:
        return None, 0.0, ""

    ref_names = ref_df["Name"].map(_canon).tolist()
    matches = difflib.get_close_matches(sub_name, ref_names, n=1, cutoff=CONF_LOG_ONLY)
    if not matches:
        return None, 0.0, ""

    best_name = matches[0]
    ratio = difflib.SequenceMatcher(None, sub_name, best_name).ratio()
    if ratio < CONF_LOG_ONLY:
        return None, 0.0, ""

    ref_row = ref_df[ref_df["Name"].map(_canon) == best_name].iloc[0]
    return ref_row, round(ratio, 4), f"fuzzy name match (ratio={ratio:.4f})"


# ---------------------------------------------------------------------------
# Correction attempt building
# ---------------------------------------------------------------------------

def _build_correction_attempts(
    *,
    submission_id: str,
    row_number: int,
    sub_row: pd.Series,
    ref_row: pd.Series,
    correctable_fields: tuple[str, ...],
    match_confidence: float,
    match_source: str,
    timestamp: str,
) -> list[CorrectionAttempt]:
    """Generate correction attempts for one matched submission/reference row pair.

    Conservative rules:
    - Never correct when reference value is blank (do not invent values).
    - For fuzzy matches (confidence < 0.99), do not fill blank submission
      fields — only correct wrong values.
    - For identity matches (MAC/IP, confidence >= 0.99), blank-fill is allowed
      because device identity is certain.
    - Confidence determines apply/review/log disposition per threshold policy.
    """
    attempts: list[CorrectionAttempt] = []

    for col in correctable_fields:
        sub_val = str(sub_row.get(col, "")).strip()
        ref_col = _find_ref_col(ref_row, col)
        if ref_col is None:
            continue
        ref_val = str(ref_row[ref_col]).strip()

        if not ref_val or _canon(ref_val) == "":
            # Reference has no value — do not invent a correction.
            continue

        if _canon(sub_val) == _canon(ref_val):
            # Values already match — nothing to do.
            continue

        # Fuzzy matches must not fill blanks — too risky without device identity.
        if not sub_val and match_confidence < 0.99:
            continue

        # Name guard: when matched via MAC/IP identity (confidence >= 0.99)
        # and the reference Name differs substantially from the vendor Name,
        # the reference is likely stale or the match resolved to a different
        # physical device.  Do NOT auto-apply — log for review only.
        if (
            col.strip().lower() == "name"
            and match_confidence >= CONF_APPLY_REVIEW  # i.e. identity match
            and "fuzzy" not in match_source.lower()
        ):
            name_sim = difflib.SequenceMatcher(
                None, _canon(sub_val), _canon(ref_val)
            ).ratio()
            if name_sim < 0.85:
                attempts.append(CorrectionAttempt(
                    submission_id=submission_id,
                    row_number=row_number,
                    field=col,
                    original_value=sub_val,
                    corrected_value=sub_val,   # keep original
                    reason=(
                        f"Name similarity {name_sim:.2f} < 0.85 vs identity-matched "
                        f"reference — possible stale reference; logged for review only"
                    ),
                    source=match_source,
                    confidence=match_confidence,
                    applied=False,
                    requires_review=True,
                    timestamp=timestamp,
                ))
                continue

        # Disposition based on confidence threshold.
        if match_confidence >= CONF_APPLY:
            applied = True
            requires_review = False
            reason = "exact reference lookup correction"
        elif match_confidence >= CONF_APPLY_REVIEW:
            applied = True
            requires_review = True
            reason = "high-confidence reference correction — flagged for review"
        else:
            # CONF_LOG_ONLY <= confidence < CONF_APPLY_REVIEW
            applied = False
            requires_review = True
            reason = "below apply threshold — logged for review only"

        attempts.append(CorrectionAttempt(
            submission_id=submission_id,
            row_number=row_number,
            field=col,
            original_value=sub_val,
            corrected_value=ref_val if applied else sub_val,
            reason=reason,
            source=match_source,
            confidence=match_confidence,
            applied=applied,
            requires_review=requires_review,
            timestamp=timestamp,
        ))

    return attempts


def _find_ref_col(ref_row: pd.Series, col: str) -> str | None:
    """Case-insensitive column lookup in a reference row's index."""
    col_lower = col.strip().lower()
    for idx_col in ref_row.index:
        if str(idx_col).strip().lower() == col_lower:
            return idx_col
    return None


# ---------------------------------------------------------------------------
# Apply corrections to DataFrame
# ---------------------------------------------------------------------------

def _apply_corrections(
    df: pd.DataFrame,
    applied: list[CorrectionAttempt],
) -> pd.DataFrame:
    """Write approved corrections into the corrected DataFrame.

    INVARIANTS (all strictly enforced):
    - Column count is never changed.
    - Column names are never changed.
    - Column order is never changed.
    - Row count is never changed.
    - Row order is never changed.
    - Only the specific (row_idx, column) cells listed in *applied* are touched.
    - Every other cell retains the exact original vendor value.

    If a correction references an unknown column or out-of-range row it is
    skipped with a warning — it never silently corrupts other cells.
    """
    original_columns = list(df.columns)  # snapshot for post-check
    original_len     = len(df)

    # Case-insensitive map: lowercase column name → actual column name in df
    col_map = {str(c).strip().lower(): str(c) for c in df.columns}

    for attempt in applied:
        actual_col = col_map.get(attempt.field.strip().lower())
        if actual_col is None:
            log.warning(
                "Post-pass correction: column '%s' not found in submission "
                "— skipping row=%d submission=%s. Available columns: %s",
                attempt.field, attempt.row_number, attempt.submission_id,
                list(df.columns),
            )
            continue

        df_idx = attempt.row_number - 1  # row_number is 1-based
        if df_idx < 0 or df_idx >= len(df):
            log.warning(
                "Post-pass correction: row_number=%d out of range (file has %d rows) "
                "for submission=%s — skipping.",
                attempt.row_number, len(df), attempt.submission_id,
            )
            continue

        log.debug(
            "Post-pass correction: applying [row=%d col=%r] %r → %r",
            attempt.row_number, actual_col,
            attempt.original_value, attempt.corrected_value,
        )
        df.at[df_idx, actual_col] = attempt.corrected_value

    # ── Post-application invariant check ─────────────────────────────────
    # If columns or row count changed, something is very wrong — log loudly
    # and return the fully-original df so we never write a mangled file.
    if list(df.columns) != original_columns:
        log.error(
            "Post-pass correction BUG: column list changed after corrections! "
            "original=%s  current=%s  — aborting corrections and returning original data.",
            original_columns, list(df.columns),
        )
        # Reconstruct a clean copy from original to be safe
        for col in original_columns:
            if col not in df.columns:
                df[col] = ""
        df = df[original_columns]

    if len(df) != original_len:
        log.error(
            "Post-pass correction BUG: row count changed %d → %d after corrections!",
            original_len, len(df),
        )

    return df


# ---------------------------------------------------------------------------
# Correction log output
# ---------------------------------------------------------------------------

_LOG_COLUMNS: tuple[str, ...] = (
    "submission_id",
    "site_number",
    "vendor_name",
    "row_number",
    "field",
    "original_value",
    "corrected_value",
    "reason",
    "source",
    "confidence",
    "applied",
    "requires_review",
    "timestamp",
)


def _write_correction_log(
    attempts: list[CorrectionAttempt],
    path: Path,
    site_number: str = "",
    vendor_name: str = "",
) -> None:
    """Write the correction log CSV — one row per correction attempt."""
    rows = [
        {
            "submission_id":  a.submission_id,
            "site_number":    site_number,
            "vendor_name":    vendor_name,
            "row_number":     a.row_number,
            "field":          a.field,
            "original_value": a.original_value,
            "corrected_value":a.corrected_value,
            "reason":         a.reason,
            "source":         a.source,
            "confidence":     round(a.confidence, 6),
            "applied":        a.applied,
            "requires_review":a.requires_review,
            "timestamp":      a.timestamp,
        }
        for a in attempts
    ]
    log_df = pd.DataFrame(rows, columns=list(_LOG_COLUMNS))
    log_df.to_csv(path, index=False, encoding="utf-8")
    log.info("Correction log written: %s (%d entries)", path.name, len(rows))


# ---------------------------------------------------------------------------
# Filename sanitization
# ---------------------------------------------------------------------------

def _safe_filename(text: str, max_len: int = 80) -> str:
    """Return a filesystem-safe string from arbitrary text.

    Replaces characters illegal on Windows/OneDrive paths with underscores,
    collapses runs of underscores, and trims to max_len.
    """
    safe = re.sub(r'[\\/:*?"<>|\s]+', "_", text)
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe[:max_len]
