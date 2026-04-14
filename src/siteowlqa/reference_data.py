"""Reference data access for SiteOwlQA.

One module, one job: provide site-scoped reference rows and site profiles
from the configured source of truth.

Supported sources:
- sql    -> dbo.vw_ReferenceNormalized via pyodbc
- excel  -> cleaned workbook keyed by Site ID (preferred when SQL import is bad)
- auto   -> workbook when configured/available, otherwise SQL

Because duplicating lookup logic in multiple modules is how bugs breed.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from siteowlqa.config import AppConfig, VENDOR_GRADE_COLUMNS, VENDOR_HEADER_ALIASES
from siteowlqa.sql import fetch_reference_rows_from_sql
from siteowlqa.bigquery_provider import fetch_reference_rows_from_bigquery
from siteowlqa.utils import canon_site_id

log = logging.getLogger(__name__)

# VENDOR_HEADER_ALIASES is the single source of truth for column alias mapping.
# Imported from config — do NOT redefine here.

OPTIONAL_PROFILE_COLUMNS: tuple[str, ...] = (
    "Abbreviated Name",
    "Description",
)


@dataclass(frozen=True)
class SiteReferenceProfile:
    site_number: str
    reference_row_count: int
    has_reference_rows: bool
    optional_fields_populated: dict[str, bool]



def fetch_reference_rows(cfg: AppConfig, site_number: str) -> pd.DataFrame:
    """Return canonical reference rows for one site from the active source."""
    source = _resolve_reference_source(cfg)
    if source == "excel":
        workbook_path = _require_workbook_path(cfg)
        return _fetch_reference_rows_from_excel(cfg, workbook_path, site_number)
    if source == "bigquery":
        return fetch_reference_rows_from_bigquery(cfg, site_number)
    return fetch_reference_rows_from_sql(cfg, site_number)



def fetch_site_reference_profile(cfg: AppConfig, site_number: str) -> SiteReferenceProfile:
    """Return row-count/profile metadata from the active reference source."""
    df = fetch_reference_rows(cfg, site_number)
    optional_fields = {
        col: bool(df[col].astype(str).str.strip().replace("0", "").ne("").any())
        for col in OPTIONAL_PROFILE_COLUMNS
    }
    reference_row_count = len(df)
    return SiteReferenceProfile(
        site_number=site_number,
        reference_row_count=reference_row_count,
        has_reference_rows=reference_row_count > 0,
        optional_fields_populated=optional_fields,
    )



def normalize_reference_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Map raw source columns into canonical vendor-comparable columns."""
    df = raw_df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    lower_to_actual = {str(col).strip().lower(): str(col).strip() for col in df.columns}

    rename_map: dict[str, str] = {}
    for canonical, aliases in VENDOR_HEADER_ALIASES.items():
        actual = _find_first_matching_column(lower_to_actual, aliases)
        if actual is not None:
            rename_map[actual] = canonical

    if rename_map:
        df = df.rename(columns=rename_map)

    for col in VENDOR_GRADE_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df[list(VENDOR_GRADE_COLUMNS)].fillna("").astype(str)



def _resolve_reference_source(cfg: AppConfig) -> str:
    source = (cfg.reference_source or "sql").strip().lower()
    if source not in {"sql", "excel", "auto", "bigquery"}:
        raise ValueError(
            f"Unsupported REFERENCE_SOURCE='{cfg.reference_source}'. "
            "Expected one of: sql, excel, auto, bigquery."
        )
    if source == "auto":
        return "excel" if cfg.reference_workbook_path else "sql"
    if source == "excel" and not cfg.reference_workbook_path:
        raise ValueError(
            "REFERENCE_SOURCE=excel requires REFERENCE_WORKBOOK_PATH or an auto-detected workbook."
        )
    return source



def _require_workbook_path(cfg: AppConfig) -> Path:
    path = cfg.reference_workbook_path
    if path is None:
        raise ValueError("Reference workbook path is not configured.")
    if not path.exists():
        raise FileNotFoundError(f"Reference workbook not found: {path}")
    return path



# ---------------------------------------------------------------------------
# Thread-safe reference workbook cache
#
# Why not @lru_cache?
# lru_cache is NOT thread-safe for concurrent WRITES: if two worker threads
# both hit a cache miss at the same moment, both will call pd.read_excel on
# the 207K-row workbook simultaneously — the classic "cache stampede".
# This double-checked locking pattern ensures only ONE thread ever loads;
# all others block and then reuse the result.
# ---------------------------------------------------------------------------

_cache_lock = threading.Lock()
# Cache key includes workbook fingerprint so updates on disk invalidate stale data.
# key = (path, sheet, site_id_column, mtime_ns, file_size)
_workbook_cache: dict[tuple[str, str, str, int, int], dict[str, pd.DataFrame]] = {}


def clear_reference_workbook_cache() -> None:
    """Clear in-memory workbook cache.

    Primarily for tests and operational troubleshooting.
    """
    with _cache_lock:
        _workbook_cache.clear()


def prewarm_reference_cache(cfg: AppConfig) -> None:
    """Load the reference workbook into memory now, in a background thread.

    Call this once at startup so the first real submission hits a warm cache
    instead of waiting 35+ seconds for the 207K-row workbook to load.
    The load runs in whatever thread calls this function; use a daemon thread
    in main.py so startup isn't blocked.
    """
    source = _resolve_reference_source(cfg)
    if source != "excel":
        log.info("Prewarm skipped — reference source is '%s', not excel.", source)
        return
    try:
        workbook_path = _require_workbook_path(cfg)
        log.info("Prewarming reference cache from %s ...", workbook_path)
        _load_reference_workbook(
            str(workbook_path),
            cfg.reference_workbook_sheet,
            cfg.reference_workbook_site_id_column,
        )
        log.info("Reference cache prewarm complete.")
    except Exception as exc:  # noqa: BLE001
        log.warning("Reference cache prewarm failed (non-fatal): %s", exc)


def _load_reference_workbook(
    workbook_path_str: str,
    sheet_name: str,
    site_id_column: str,
) -> dict[str, pd.DataFrame]:
    """Load and cache the reference workbook. Thread-safe via double-checked lock."""
    workbook_path = Path(workbook_path_str)
    stat = workbook_path.stat()
    key = (
        workbook_path_str,
        sheet_name,
        site_id_column,
        int(stat.st_mtime_ns),
        int(stat.st_size),
    )

    # Fast path: already cached — no lock needed for reads (dict lookup is atomic in CPython).
    cached = _workbook_cache.get(key)
    if cached is not None:
        return cached

    # Slow path: acquire lock so only ONE thread loads the workbook.
    with _cache_lock:
        # Re-check inside the lock — another thread may have loaded while we waited.
        cached = _workbook_cache.get(key)
        if cached is not None:
            return cached

        selected_sheet = 0 if not sheet_name else sheet_name

        # Try calamine first (Rust-based, 5-10× faster than openpyxl).
        # Fall back to openpyxl if calamine isn't installed or the file isn't supported.
        try:
            raw_df = pd.read_excel(
                workbook_path,
                sheet_name=selected_sheet,
                dtype=str,
                engine="calamine",
            )
        except Exception:
            log.debug("calamine unavailable; falling back to openpyxl for reference workbook.")
            raw_df = pd.read_excel(
                workbook_path,
                sheet_name=selected_sheet,
                dtype=str,
                engine="openpyxl",
            )

        raw_df.columns = [str(col).strip() for col in raw_df.columns]

        site_id_actual = _find_required_column(raw_df.columns, site_id_column)
        canonical_df = normalize_reference_dataframe(raw_df)
        canonical_df["__site_lookup_key__"] = raw_df[site_id_actual].map(canon_site_id)

        grouped: dict[str, pd.DataFrame] = {}
        for site_key, group in canonical_df.groupby(
            "__site_lookup_key__", dropna=False, sort=False
        ):
            group_df = group.drop(columns=["__site_lookup_key__"]).reset_index(drop=True)
            if site_key:
                grouped[site_key] = group_df

        log.info(
            "Loaded workbook reference data: path=%s sheet=%s site_groups=%d rows=%d",
            workbook_path,
            sheet_name or "<first>",
            len(grouped),
            len(canonical_df),
        )

        _workbook_cache[key] = grouped
        return grouped



def _fetch_reference_rows_from_excel(
    cfg: AppConfig,
    workbook_path: Path,
    site_number: str,
) -> pd.DataFrame:
    grouped = _load_reference_workbook(
        str(workbook_path),
        cfg.reference_workbook_sheet,
        cfg.reference_workbook_site_id_column,
    )
    df = grouped.get(canon_site_id(site_number))
    if df is None:
        return pd.DataFrame(columns=list(VENDOR_GRADE_COLUMNS))
    return df.copy()



def _find_first_matching_column(
    lower_to_actual: dict[str, str],
    aliases: tuple[str, ...],
) -> str | None:
    for alias in aliases:
        actual = lower_to_actual.get(alias.strip().lower())
        if actual is not None:
            return actual
    return None


# Known fallback aliases for the site-ID lookup column in the reference workbook.
# SelectedSiteID is the primary name; everything below is a recovery alias.
# This column is INTERNAL TO THE WORKBOOK ONLY — it is never a graded field
# and is never expected to appear in any vendor submission.
_SITE_ID_COLUMN_ALIASES: tuple[str, ...] = (
    "SelectedSiteID",
    "Selected Site ID",
    "SiteID",
    "Site ID",
    "Site Number",
    "SiteNumber",
    "ProjectID",
    "Project ID",
)


def _find_required_column(columns: pd.Index, primary_name: str) -> str:
    """Locate the site-ID lookup column in the reference workbook.

    Tries the configured column name first (case-insensitive), then works
    through _SITE_ID_COLUMN_ALIASES automatically so a minor workbook rename
    never hard-crashes the pipeline.

    This column is strictly a workbook-internal lookup key — it is NEVER
    treated as a graded field and is NEVER expected in vendor submissions.
    """
    lower_to_actual = {str(col).strip().lower(): str(col).strip() for col in columns}

    # 1. Try the configured name exactly (case-insensitive).
    actual = lower_to_actual.get(primary_name.strip().lower())
    if actual is not None:
        return actual

    # 2. Try every known alias before giving up.
    all_candidates = (primary_name,) + _SITE_ID_COLUMN_ALIASES
    for alias in all_candidates:
        actual = lower_to_actual.get(alias.strip().lower())
        if actual is not None:
            log.warning(
                "Reference workbook: configured site-id column '%s' not found. "
                "Using '%s' as a fallback. "
                "To silence this warning, set REFERENCE_WORKBOOK_SITE_ID_COLUMN=%s "
                "in your .env or user config.",
                primary_name, actual, actual,
            )
            return actual

    # 3. Nothing matched — show EVERY available column so the operator
    #    can see exactly what the workbook has (no more truncated empties).
    all_cols_str = ", ".join(f"'{c}'" for c in columns) or "(none — workbook may be empty or the wrong sheet is configured)"
    raise ValueError(
        f"Reference workbook has no recognisable site-id lookup column. "
        f"Configured name: '{primary_name}'. "
        f"Also tried: {', '.join(repr(a) for a in _SITE_ID_COLUMN_ALIASES[1:])}. "
        f"Columns actually in workbook: {all_cols_str}"
    )
