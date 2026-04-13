"""file_processor.py — Vendor file loading and normalisation.

Responsibilities:
 - Read XLSX or CSV vendor export files
 - Case/alias-insensitive column matching to grade headers
 - Add missing grade columns as empty string (don't fail on partial files)
 - Ignore vendor extra columns (vendors may send 56+ cols)
 - Return a clean DataFrame ready for Python-side comparison

This module does NOT touch SQL or Airtable — pure data transformation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from siteowlqa.config import VENDOR_GRADE_COLUMNS, VENDOR_HEADER_ALIASES

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class VendorFileLoadResult:
    dataframe: pd.DataFrame
    raw_columns: list[str]
    normalized_columns: list[str]
    missing_required_columns: list[str]
    extra_columns: list[str]


def load_vendor_file(file_path: Path, site_number: str) -> pd.DataFrame:
    """Load a vendor export file and return a clean, normalised DataFrame.

    Processing steps:
    1. Detect file type from extension (.xlsx or .csv)
    2. Load into pandas with all columns as strings
    3. Strip whitespace from column headers
    4. Case-insensitive rename to canonical header form
    5. Add any missing grade columns as empty strings
    6. Ignore extra columns
    7. Replace NaN with empty string

    Args:
        file_path:   Local path to the downloaded vendor file.
        site_number: Airtable Site Number (used for reference lookup elsewhere).

    Returns:
        Normalised DataFrame. Always has all grade columns present.

    Raises:
        ValueError:  Unsupported file extension, or file is completely empty.
        IOError:     File cannot be read.
    """
    return load_vendor_file_with_metadata(file_path, site_number).dataframe


def load_vendor_file_with_metadata(
    file_path: Path,
    site_number: str,
) -> VendorFileLoadResult:
    """Load a vendor export file and return the dataframe plus schema metadata."""
    suffix = file_path.suffix.lower()
    log.info("Loading vendor file: %s (ext=%s)", file_path.name, suffix)

    df = _read_file(file_path, suffix)

    if df.empty:
        raise ValueError(
            f"Vendor file '{file_path.name}' is empty after reading. "
            "Check the uploaded file."
        )

    raw_columns = [str(c).strip() for c in df.columns]
    log.info("Raw shape: %d rows x %d cols", *df.shape)

    df = _normalise_headers(df)
    normalized_columns = [str(c).strip() for c in df.columns]
    extra_columns = [
        col for col in normalized_columns
        if col not in VENDOR_GRADE_COLUMNS
    ]
    df = _ensure_grade_columns(df)
    df = _derive_grade_fields(df)

    # Compute missing grade columns AFTER derivations.
    missing_required_columns: list[str] = []
    for col in VENDOR_GRADE_COLUMNS:
        series = df[col].fillna("").astype(str).str.strip()
        if series.eq("").all():
            missing_required_columns.append(col)

    # NOTE: We intentionally do NOT require/overwrite "Project ID" or "Plan ID".
    # Airtable Site Number is used separately to scope the reference lookup.
    df = df.fillna("").infer_objects(copy=False)

    log.info(
        "Normalised shape: %d rows x %d cols | site=%s",
        *df.shape,
        site_number,
    )
    return VendorFileLoadResult(
        dataframe=df,
        raw_columns=raw_columns,
        normalized_columns=normalized_columns,
        missing_required_columns=missing_required_columns,
        extra_columns=extra_columns,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _read_file(path: Path, suffix: str) -> pd.DataFrame:
    """Read XLSX or CSV into a pandas DataFrame with all-string dtypes."""
    if suffix == ".xlsx":
        return _read_xlsx(path)
    if suffix == ".csv":
        return _read_csv_with_fallback(path)
    raise ValueError(
        f"Unsupported vendor file type '{suffix}'. "
        "Only .xlsx and .csv are accepted."
    )


def _read_xlsx(path: Path) -> pd.DataFrame:
    """Read XLSX using calamine (fast Rust-based engine) with openpyxl fallback.

    calamine is typically 5-10x faster than openpyxl for read-only loading,
    which cuts vendor file load time from ~5s down to under 1s.
    Falls back silently to openpyxl if calamine is unavailable.
    """
    try:
        return pd.read_excel(path, sheet_name=0, dtype=str, engine="calamine")
    except Exception:
        log.debug("calamine unavailable for vendor file; falling back to openpyxl.")
        return pd.read_excel(path, sheet_name=0, dtype=str, engine="openpyxl")


def _read_csv_with_fallback(path: Path) -> pd.DataFrame:
    """Read CSV, trying UTF-8 first then latin-1 as fallback."""
    try:
        return pd.read_csv(path, dtype=str, encoding="utf-8")
    except UnicodeDecodeError:
        log.warning(
            "UTF-8 decode failed for '%s' — retrying with latin-1.",
            path.name,
        )
        return pd.read_csv(path, dtype=str, encoding="latin-1")


def _normalise_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace and perform case-insensitive rename to canonical form.

    Only renames columns that match a required column name case-insensitively.
    Unknown extra columns are preserved (they don't hurt and may be useful).
    """
    df.columns = [str(c).strip() for c in df.columns]

    # Build alias lookup: lowercase alias -> canonical.
    alias_lower_to_canonical: dict[str, str] = {}
    for canonical, aliases in VENDOR_HEADER_ALIASES.items():
        for alias in aliases:
            alias_lower_to_canonical[alias.strip().lower()] = canonical

    rename_map: dict[str, str] = {}
    for col in df.columns:
        canonical = alias_lower_to_canonical.get(str(col).strip().lower())
        if canonical and col != canonical:
            rename_map[col] = canonical

    if rename_map:
        log.info("Column rename map applied: %s", rename_map)
        df = df.rename(columns=rename_map)

    return df


def _derive_grade_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Best-effort derivations from common vendor export formats.

    Vendors often submit exports with different header sets (e.g. camera exports).
    We derive our canonical grade fields without touching the raw data beyond
    filling blanks.

    Rules:
    - If IP Address present and IP / Analog blank -> set IP / Analog = "IP"
    - If Description blank and 'model' present -> Description = model
    - If Part Number / Manufacturer blank but CategoryName present, attempt:
        CategoryName like: "<PART>-<MANUFACTURER>_..." or "<PART>-<MANUFACTURER>"
    """
    work = df.copy()

    if "IP Address" in work.columns and "IP / Analog" in work.columns:
        ip_has = work["IP Address"].astype(str).str.strip().ne("")
        ipa_blank = work["IP / Analog"].astype(str).str.strip().eq("")
        work.loc[ip_has & ipa_blank, "IP / Analog"] = "IP"

    # Many camera exports have a long human-readable model string.
    # The reference sheet often uses that as Part Number.
    if "Part Number" in work.columns and "model" in work.columns:
        pn_blank = work["Part Number"].astype(str).str.strip().eq("")
        work.loc[pn_blank, "Part Number"] = work.loc[pn_blank, "model"].fillna("")

    if "Description" in work.columns and "model" in work.columns:
        desc_blank = work["Description"].astype(str).str.strip().eq("")
        work.loc[desc_blank, "Description"] = work.loc[desc_blank, "model"].fillna("")

    if "CategoryName" in work.columns:
        cat = work["CategoryName"].fillna("").astype(str)
        # Split on '_' first (strip long suffixes), then split on first '-'
        base = cat.str.split("_", n=1).str[0]
        parts = base.str.split("-", n=1, expand=True)
        if parts.shape[1] == 2:
            part_number_guess = parts[0].fillna("").astype(str).str.strip()
            manufacturer_guess = parts[1].fillna("").astype(str).str.strip()

            if "Part Number" in work.columns:
                pn_blank = work["Part Number"].astype(str).str.strip().eq("")
                work.loc[pn_blank, "Part Number"] = part_number_guess[pn_blank]

            if "Manufacturer" in work.columns:
                m_blank = work["Manufacturer"].astype(str).str.strip().eq("")
                work.loc[m_blank, "Manufacturer"] = manufacturer_guess[m_blank]

    return work


def _ensure_grade_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure the 8 grade columns exist; everything else is ignored."""
    for col in VENDOR_GRADE_COLUMNS:
        if col not in df.columns:
            log.warning(
                "Grade column '%s' not found in vendor file — adding as empty.",
                col,
            )
            df[col] = ""
    return df
