"""reload_reference_from_two_sheets.py

Replaces the SQL reference tables (ReferenceRaw + ReferenceExport) from two
worksheets inside:

    Camera&Alarm Ref Data.xlsx
        - Sheet 1: 'CDFD1 P1'  (loaded first)
        - Sheet 2: 'CDFD1 P2'  (appended second)

The two sheets are concatenated in order, normalized with the same logic used
everywhere else in the pipeline, then bulk-inserted into SQL Server.

All grading logic is UNCHANGED.  Only the data source path differs.

Expected output: ~1.8 M rows across 58 source columns -> 9 SQL columns.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for _p in (str(SRC_ROOT), str(PROJECT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from siteowlqa.config import load_config
from siteowlqa.reference_data import normalize_reference_dataframe
from siteowlqa.sql import get_connection
from siteowlqa.utils import canon_site_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Source configuration
# ---------------------------------------------------------------------------
WORKBOOK_PATH = Path(
    r"C:\Users\vn59j7j\OneDrive - Walmart Inc"
    r"\Documents\BaselinePrinter\Excel\Camera&Alarm Ref Data.xlsx"
)
SHEET_ORDER = ["CDFD1 P1", "CDFD1 P2"]   # P1 first, P2 appended
SITE_ID_COLUMN = "SelectedSiteID"          # maps to SQL ProjectID

# ---------------------------------------------------------------------------
# SQL configuration (identical to reload_reference_raw_from_workbook.py)
# ---------------------------------------------------------------------------
REFERENCE_RAW_TABLE = "dbo.ReferenceRaw"
REFERENCE_EXPORT_TABLE = "dbo.ReferenceExport"
BATCH_SIZE = 50_000

TARGET_COLUMNS: list[str] = [
    "ProjectID",
    "Name",
    "AbbreviatedName",
    "Description",
    "PartNumber",
    "Manufacturer",
    "IPAddress",
    "MACAddress",
    "IPAnalog",
]

_PLACEHOLDERS = "(?, ?, ?, ?, ?, ?, ?, ?, ?)"
RAW_INSERT_SQL = (
    f"INSERT INTO {REFERENCE_RAW_TABLE} "
    "(ProjectID, Name, AbbreviatedName, Description, "
    "PartNumber, Manufacturer, IPAddress, MACAddress, IPAnalog) "
    f"VALUES {_PLACEHOLDERS}"
)
EXPORT_INSERT_SQL = (
    f"INSERT INTO {REFERENCE_EXPORT_TABLE} "
    "(ProjectID, Name, AbbreviatedName, Description, "
    "PartNumber, Manufacturer, IPAddress, MACAddress, IPAnalog) "
    f"VALUES {_PLACEHOLDERS}"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _canon(value: object) -> str:
    """Canonical site-ID string; suppresses bare '0' sentinel."""
    text = canon_site_id(value)
    return "" if text == "0" else text


def _read_sheet(workbook: Path, sheet_name: str) -> pd.DataFrame:
    """Read one sheet, trying calamine (fast) then openpyxl (safe fallback)."""
    log.info("  Reading sheet '%s' ...", sheet_name)
    t0 = time.time()
    try:
        df = pd.read_excel(
            workbook,
            sheet_name=sheet_name,
            dtype=str,
            engine="calamine",
        )
        engine_used = "calamine"
    except Exception:
        log.debug("calamine unavailable; falling back to openpyxl.")
        df = pd.read_excel(
            workbook,
            sheet_name=sheet_name,
            dtype=str,
            engine="openpyxl",
        )
        engine_used = "openpyxl"

    log.info(
        "  Sheet '%s': %d rows x %d cols  [engine=%s  %.1fs]",
        sheet_name,
        len(df),
        len(df.columns),
        engine_used,
        time.time() - t0,
    )
    return df


def _normalize_to_sql_tuples(combined_df: pd.DataFrame) -> list[tuple]:
    """Normalize the combined dataframe to SQL-ready tuples.

    Uses the same normalize_reference_dataframe() as the live pipeline,
    so column-alias rules stay in one place (config.py / reference_data.py).
    """
    if SITE_ID_COLUMN not in combined_df.columns:
        available = ", ".join(str(c) for c in list(combined_df.columns)[:30])
        raise ValueError(
            f"Site-ID column '{SITE_ID_COLUMN}' not found in workbook data. "
            f"Available columns (first 30): {available}"
        )

    # normalize_reference_dataframe maps vendor column aliases -> canonical names
    normalized = normalize_reference_dataframe(combined_df)

    # Pull ProjectID from the raw frame (normalize_reference_dataframe doesn't touch it)
    normalized["ProjectID"] = combined_df[SITE_ID_COLUMN].map(canon_site_id)

    # Rename canonical vendor names -> SQL column names
    normalized = normalized.rename(
        columns={
            "Abbreviated Name": "AbbreviatedName",
            "Part Number":      "PartNumber",
            "IP Address":       "IPAddress",
            "MAC Address":      "MACAddress",
            "IP / Analog":      "IPAnalog",
        }
    )

    # Ensure every target column exists and apply site-ID canonicalization
    for col in TARGET_COLUMNS:
        if col not in normalized.columns:
            normalized[col] = ""
        normalized[col] = normalized[col].map(_canon)

    return list(normalized[TARGET_COLUMNS].itertuples(index=False, name=None))


def _bulk_insert_batched(
    cur,
    sql: str,
    rows: list[tuple],
    label: str,
) -> None:
    """INSERT rows in BATCH_SIZE chunks, logging progress."""
    total = len(rows)
    cur.fast_executemany = True
    for start in range(0, total, BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        cur.executemany(sql, batch)
        done = min(start + BATCH_SIZE, total)
        log.info("  %s: %d / %d rows (%.0f%%)", label, done, total, done / total * 100)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    cfg = load_config()

    if not WORKBOOK_PATH.exists():
        raise SystemExit(f"Workbook not found: {WORKBOOK_PATH}")

    print("=" * 65)
    print(" SiteOwlQA — Reference DB Reload (Two-Sheet Append)")
    print("=" * 65)
    print(f" WORKBOOK   : {WORKBOOK_PATH.name}")
    print(f" SHEETS     : {' -> '.join(SHEET_ORDER)}")
    print(f" SITE_COL   : {SITE_ID_COLUMN}")
    print(f" BATCH_SIZE : {BATCH_SIZE:,}")
    print("=" * 65)

    t_start = time.time()

    # -------------------------------------------------------------------
    # Step 1 — Read both sheets and concatenate (P1 first, P2 second)
    # -------------------------------------------------------------------
    log.info("Step 1/3 — Reading workbook sheets...")
    frames: list[pd.DataFrame] = []
    for sheet_name in SHEET_ORDER:
        frames.append(_read_sheet(WORKBOOK_PATH, sheet_name))

    combined = pd.concat(frames, ignore_index=True)
    del frames   # free memory before normalization

    log.info(
        "Combined: %d rows x %d cols (P1=%d  P2=TBD — see above)",
        len(combined),
        len(combined.columns),
        len(combined),  # just a placeholder; individual counts already logged
    )
    print(f"\nCOMBINED_ROW_COUNT  = {len(combined):,}")
    print(f"COMBINED_COL_COUNT  = {len(combined.columns)}")

    # -------------------------------------------------------------------
    # Step 2 — Normalize columns -> SQL-ready tuples
    # -------------------------------------------------------------------
    log.info("Step 2/3 — Normalizing %d rows...", len(combined))
    insert_rows = _normalize_to_sql_tuples(combined)
    del combined   # free memory before SQL write
    log.info("Normalized: %d rows ready for SQL insert.", len(insert_rows))

    # -------------------------------------------------------------------
    # Step 3 — Truncate + bulk insert
    # -------------------------------------------------------------------
    log.info("Step 3/3 — Writing to SQL Server...")
    with get_connection(cfg, autocommit=False) as conn:
        cur = conn.cursor()

        cur.execute(f"SELECT COUNT(*) FROM {REFERENCE_RAW_TABLE}")
        before_raw = int(cur.fetchone()[0])
        cur.execute(f"SELECT COUNT(*) FROM {REFERENCE_EXPORT_TABLE}")
        before_export = int(cur.fetchone()[0])

        print(f"BEFORE_RAW_COUNT    = {before_raw:,}")
        print(f"BEFORE_EXPORT_COUNT = {before_export:,}")
        print(f"WORKBOOK_ROW_COUNT  = {len(insert_rows):,}")

        log.info("Truncating %s and %s ...", REFERENCE_RAW_TABLE, REFERENCE_EXPORT_TABLE)
        cur.execute(f"TRUNCATE TABLE {REFERENCE_RAW_TABLE}")
        cur.execute(f"TRUNCATE TABLE {REFERENCE_EXPORT_TABLE}")

        t_sql = time.time()
        _bulk_insert_batched(cur, RAW_INSERT_SQL,    insert_rows, "ReferenceRaw")
        _bulk_insert_batched(cur, EXPORT_INSERT_SQL, insert_rows, "ReferenceExport")
        log.info("SQL insert complete in %.1fs.", time.time() - t_sql)

        # Verify row counts
        cur.execute(f"SELECT COUNT(*) FROM {REFERENCE_RAW_TABLE}")
        after_raw = int(cur.fetchone()[0])
        cur.execute(f"SELECT COUNT(*) FROM {REFERENCE_EXPORT_TABLE}")
        after_export = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM dbo.vw_ReferenceNormalized")
        view_count = int(cur.fetchone()[0])

        expected = len(insert_rows)
        if after_raw != expected:
            raise RuntimeError(
                f"ReferenceRaw mismatch: inserted={expected:,}  table={after_raw:,}"
            )
        if after_export != expected:
            raise RuntimeError(
                f"ReferenceExport mismatch: inserted={expected:,}  table={after_export:,}"
            )
        if view_count != after_export:
            raise RuntimeError(
                f"View mismatch: export={after_export:,}  view={view_count:,}"
            )

        # Spot-check sample rows
        cur.execute(
            """
            SELECT TOP 5 ProjectID, Name, PartNumber, Manufacturer
            FROM dbo.vw_ReferenceNormalized
            ORDER BY ProjectID, Name
            """
        )
        print("\nSAMPLE ROWS (top 5 from vw_ReferenceNormalized):")
        for row in cur.fetchall():
            print("  " + " | ".join("" if v is None else str(v) for v in row))

    total_time = time.time() - t_start
    print("\n" + "=" * 65)
    print(f" AFTER_RAW_COUNT     = {after_raw:,}")
    print(f" AFTER_EXPORT_COUNT  = {after_export:,}")
    print(f" VIEW_COUNT          = {view_count:,}")
    print(f" TOTAL_TIME          = {total_time:.1f}s")
    print(" STATUS              = COMPLETE")
    print("=" * 65)


if __name__ == "__main__":
    main()
