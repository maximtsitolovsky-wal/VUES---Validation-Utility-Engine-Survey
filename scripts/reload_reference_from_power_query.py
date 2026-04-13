"""reload_reference_from_power_query.py

Replaces the SQL reference tables (ReferenceRaw + ReferenceExport) from a
Power Query named 'CDFD1' inside an Excel workbook whose result set exceeds
Excel's 1,048,576-row sheet limit.

Strategy:
  1. Open the workbook via COM (Excel.Application).
  2. Try to find CDFD1 as a visible or hidden ListObject on any worksheet.
  3. If the data is ONLY in the Power Pivot Data Model (row count > sheet limit),
     connect via ADO/MSOLAP and stream rows in batches.
  4. Normalize using the exact same logic as reload_reference_raw_from_workbook.py.
  5. Truncate + bulk-insert ReferenceRaw and ReferenceExport.
  6. Verify row counts against dbo.vw_ReferenceNormalized.

All grading logic is unchanged — only the extraction method differs.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Iterator

import pandas as pd
import pythoncom
import win32com.client

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
# Configuration — edit these if the workbook or query name changes
# ---------------------------------------------------------------------------
WORKBOOK_PATH = Path(
    r"C:\Users\vn59j7j\OneDrive - Walmart Inc\CamDataRAW.xlsx"
)
QUERY_NAME = "CDFD1"          # Power Query name inside the workbook
SITE_ID_COLUMN = "SelectedSiteID"  # Column that maps to SQL ProjectID
BATCH_SIZE = 50_000            # Rows per SQL executemany call

# ---------------------------------------------------------------------------
# SQL constants (identical to reload_reference_raw_from_workbook.py)
# ---------------------------------------------------------------------------
REFERENCE_RAW_TABLE = "dbo.ReferenceRaw"
REFERENCE_EXPORT_TABLE = "dbo.ReferenceExport"

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

_INSERT_PLACEHOLDERS = "(?, ?, ?, ?, ?, ?, ?, ?, ?)"
RAW_INSERT_SQL = (
    f"INSERT INTO {REFERENCE_RAW_TABLE} "
    f"(ProjectID, Name, AbbreviatedName, Description, "
    f"PartNumber, Manufacturer, IPAddress, MACAddress, IPAnalog) "
    f"VALUES {_INSERT_PLACEHOLDERS}"
)
EXPORT_INSERT_SQL = (
    f"INSERT INTO {REFERENCE_EXPORT_TABLE} "
    f"(ProjectID, Name, AbbreviatedName, Description, "
    f"PartNumber, Manufacturer, IPAddress, MACAddress, IPAnalog) "
    f"VALUES {_INSERT_PLACEHOLDERS}"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _canon(value: object) -> str:
    """Canonical site-ID string; suppresses bare '0' sentinel."""
    text = canon_site_id(value)
    return "" if text == "0" else text


def _normalize_to_sql_tuples(raw_df: pd.DataFrame) -> list[tuple]:
    """Normalize raw dataframe columns and return SQL insert tuples.

    Uses the same normalize_reference_dataframe logic as the rest of the
    pipeline so column-mapping rules stay in one place.
    """
    if SITE_ID_COLUMN not in raw_df.columns:
        available = ", ".join(str(c) for c in list(raw_df.columns)[:30])
        raise ValueError(
            f"Site-ID column '{SITE_ID_COLUMN}' not found in extracted data. "
            f"Available columns: {available}"
        )

    normalized = normalize_reference_dataframe(raw_df)
    normalized["ProjectID"] = raw_df[SITE_ID_COLUMN].map(canon_site_id)

    # Rename canonical vendor columns -> SQL column names
    normalized = normalized.rename(
        columns={
            "Abbreviated Name": "AbbreviatedName",
            "Part Number": "PartNumber",
            "IP Address": "IPAddress",
            "MAC Address": "MACAddress",
            "IP / Analog": "IPAnalog",
        }
    )

    for col in TARGET_COLUMNS:
        if col not in normalized.columns:
            normalized[col] = ""
        normalized[col] = normalized[col].map(_canon)

    return list(normalized[TARGET_COLUMNS].itertuples(index=False, name=None))


# ---------------------------------------------------------------------------
# Extraction — Phase 1: try worksheet ListObject (fast, no COM complexity)
# ---------------------------------------------------------------------------

def _try_sheet_extraction(wb) -> pd.DataFrame | None:
    """Look for CDFD1 as a named ListObject on any sheet (visible or hidden).

    Returns a DataFrame if found, None if the data is only in the Data Model.
    """
    for ws in wb.Worksheets:
        for lo in ws.ListObjects:
            if lo.Name.upper() == QUERY_NAME.upper():
                log.info(
                    "Found '%s' as a ListObject on sheet '%s'.",
                    QUERY_NAME,
                    ws.Name,
                )
                rng = lo.DataBodyRange
                if rng is None:
                    log.warning("ListObject has no data rows.")
                    return None

                headers = [
                    lo.HeaderRowRange.Cells(1, c + 1).Value
                    for c in range(lo.HeaderRowRange.Columns.Count)
                ]
                # GetValue2 returns a 2-D tuple for multi-row ranges
                values = rng.GetValue2()
                if isinstance(values, tuple) and isinstance(values[0], tuple):
                    rows = [list(r) for r in values]
                else:
                    # Single row returns a flat tuple
                    rows = [list(values)]

                log.info(
                    "Extracted %d rows from ListObject.", len(rows)
                )
                return pd.DataFrame(rows, columns=headers)
    return None


# ---------------------------------------------------------------------------
# Extraction — Phase 2: MSOLAP / Power Pivot data model via ADO
# ---------------------------------------------------------------------------

ADO_BATCH = 10_000   # GetRows fetch size from the ADO Recordset


def _list_model_tables(conn) -> list[str]:
    """Return table names available in the embedded data model."""
    rs = win32com.client.Dispatch("ADODB.Recordset")
    try:
        rs.Open(
            "SELECT [TABLE_NAME] FROM $System.DBSCHEMA_TABLES "
            "WHERE TABLE_TYPE = 'TABLE'",
            conn,
        )
        names: list[str] = []
        while not rs.EOF:
            names.append(str(rs.Fields[0].Value))
            rs.MoveNext()
        return names
    finally:
        rs.Close()


def _iter_recordset_batches(
    rs,
    col_count: int,
) -> Iterator[list[list]]:
    """Yield row batches from an open ADO Recordset using GetRows.

    GetRows returns a column-major 2-D tuple: (col_idx, row_idx).
    We transpose to row-major for DataFrame construction.
    """
    while not rs.EOF:
        # GetRows(n) fetches up to n rows; returns tuple-of-tuples (col-major)
        chunk = rs.GetRows(ADO_BATCH)
        if not chunk:
            break
        n_cols = len(chunk)
        n_rows = len(chunk[0])
        # Transpose: chunk[col][row] -> row_data[row][col]
        rows = [
            [chunk[c][r] for c in range(n_cols)]
            for r in range(n_rows)
        ]
        yield rows


def _extract_from_data_model() -> pd.DataFrame:
    """Open Excel and extract CDFD1 from the embedded Power Pivot data model."""
    pythoncom.CoInitialize()
    xl = None
    wb = None

    try:
        log.info("Opening Excel (hidden): %s", WORKBOOK_PATH)
        xl = win32com.client.Dispatch("Excel.Application")
        xl.Visible = False
        xl.DisplayAlerts = False
        xl.ScreenUpdating = False

        wb = xl.Workbooks.Open(
            str(WORKBOOK_PATH),
            ReadOnly=True,
            UpdateLinks=0,   # 0 = don't update external links
        )
        log.info("Workbook open. Connecting to embedded data model...")

        # Connect to the in-process Analysis Services engine (Power Pivot)
        conn = win32com.client.Dispatch("ADODB.Connection")
        conn.Open("Provider=MSOLAP;Data Source=$Embedded$")

        # Enumerate tables to find the right one
        available = _list_model_tables(conn)
        log.info("Data model tables: %s", available)

        # Match CDFD1 (case-insensitive partial match as fallback)
        target = next(
            (t for t in available if t.upper() == QUERY_NAME.upper()),
            None,
        )
        if target is None:
            target = next(
                (t for t in available if QUERY_NAME.upper() in t.upper()),
                None,
            )
        if target is None:
            raise RuntimeError(
                f"Table '{QUERY_NAME}' not found in data model. "
                f"Available tables: {available}"
            )

        log.info("Querying data model table: '%s'", target)
        rs = win32com.client.Dispatch("ADODB.Recordset")
        # adOpenStatic (3) + adLockReadOnly (1) + adCmdText (1)
        rs.Open(f"EVALUATE '{target}'", conn, 3, 1)

        col_count = rs.Fields.Count
        columns = [rs.Fields[i].Name for i in range(col_count)]
        log.info("Columns (%d): %s", col_count, columns)

        all_rows: list[list] = []
        total = 0
        t0 = time.time()
        for batch in _iter_recordset_batches(rs, col_count):
            all_rows.extend(batch)
            total += len(batch)
            if total % 200_000 == 0:
                elapsed = time.time() - t0
                log.info(
                    "  ... %d rows extracted (%.1fs elapsed)",
                    total,
                    elapsed,
                )

        rs.Close()
        conn.Close()

        log.info(
            "Extraction complete: %d rows in %.1fs",
            total,
            time.time() - t0,
        )
        return pd.DataFrame(all_rows, columns=columns)

    finally:
        if wb is not None:
            try:
                wb.Close(SaveChanges=False)
            except Exception:  # noqa: BLE001
                pass
        if xl is not None:
            try:
                xl.Quit()
            except Exception:  # noqa: BLE001
                pass
        pythoncom.CoUninitialize()


# ---------------------------------------------------------------------------
# Extraction — orchestrator: sheet first, data model if needed
# ---------------------------------------------------------------------------

def extract_query_data() -> pd.DataFrame:
    """Extract CDFD1 data from the workbook, choosing the right method."""
    pythoncom.CoInitialize()
    xl = None
    wb = None
    sheet_df = None

    try:
        xl = win32com.client.Dispatch("Excel.Application")
        xl.Visible = False
        xl.DisplayAlerts = False
        wb = xl.Workbooks.Open(
            str(WORKBOOK_PATH),
            ReadOnly=True,
            UpdateLinks=0,
        )
        sheet_df = _try_sheet_extraction(wb)
    except Exception as exc:  # noqa: BLE001
        log.debug("Sheet extraction probe failed: %s", exc)
    finally:
        if wb is not None:
            try:
                wb.Close(SaveChanges=False)
            except Exception:  # noqa: BLE001
                pass
        if xl is not None:
            try:
                xl.Quit()
            except Exception:  # noqa: BLE001
                pass
        pythoncom.CoUninitialize()

    if sheet_df is not None:
        log.info(
            "Data extracted from worksheet ListObject (%d rows).",
            len(sheet_df),
        )
        return sheet_df

    log.info(
        "CDFD1 not found as a worksheet table. "
        "Falling back to Power Pivot data model extraction."
    )
    return _extract_from_data_model()


# ---------------------------------------------------------------------------
# SQL bulk-load
# ---------------------------------------------------------------------------

def _bulk_insert_batched(
    cur,
    sql: str,
    rows: list[tuple],
    label: str,
) -> None:
    """Insert rows in BATCH_SIZE chunks with progress logging."""
    total = len(rows)
    cur.fast_executemany = True
    for start in range(0, total, BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        cur.executemany(sql, batch)
        done = min(start + BATCH_SIZE, total)
        log.info("  %s: %d / %d rows", label, done, total)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    cfg = load_config()

    if not WORKBOOK_PATH.exists():
        raise SystemExit(f"Workbook not found: {WORKBOOK_PATH}")

    print("=" * 65)
    print(" SiteOwlQA — Reference DB Reload from Power Query")
    print("=" * 65)
    print(f" WORKBOOK  : {WORKBOOK_PATH}")
    print(f" QUERY     : {QUERY_NAME}")
    print(f" SITE_COL  : {SITE_ID_COLUMN}")
    print(f" BATCH_SIZE: {BATCH_SIZE:,}")
    print("=" * 65)

    # -----------------------------------------------------------------------
    # Step 1 — Extract
    # -----------------------------------------------------------------------
    log.info("Step 1/3 — Extracting data from workbook...")
    t_start = time.time()
    raw_df = extract_query_data()
    log.info("Extracted %d raw rows in %.1fs.", len(raw_df), time.time() - t_start)

    # -----------------------------------------------------------------------
    # Step 2 — Normalize
    # -----------------------------------------------------------------------
    log.info("Step 2/3 — Normalizing columns...")
    insert_rows = _normalize_to_sql_tuples(raw_df)
    log.info("Normalized: %d rows ready for SQL insert.", len(insert_rows))

    # Free the large raw frame before the SQL write
    del raw_df

    # -----------------------------------------------------------------------
    # Step 3 — SQL truncate + bulk insert
    # -----------------------------------------------------------------------
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

        log.info("Truncating reference tables...")
        cur.execute(f"TRUNCATE TABLE {REFERENCE_RAW_TABLE}")
        cur.execute(f"TRUNCATE TABLE {REFERENCE_EXPORT_TABLE}")

        t_sql = time.time()
        _bulk_insert_batched(cur, RAW_INSERT_SQL, insert_rows, "ReferenceRaw")
        _bulk_insert_batched(cur, EXPORT_INSERT_SQL, insert_rows, "ReferenceExport")
        log.info("SQL insert complete in %.1fs.", time.time() - t_sql)

        # Verify
        cur.execute(f"SELECT COUNT(*) FROM {REFERENCE_RAW_TABLE}")
        after_raw = int(cur.fetchone()[0])
        cur.execute(f"SELECT COUNT(*) FROM {REFERENCE_EXPORT_TABLE}")
        after_export = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM dbo.vw_ReferenceNormalized")
        view_count = int(cur.fetchone()[0])

        expected = len(insert_rows)
        if after_raw != expected:
            raise RuntimeError(
                f"ReferenceRaw mismatch: inserted={expected:,} table={after_raw:,}"
            )
        if after_export != expected:
            raise RuntimeError(
                f"ReferenceExport mismatch: inserted={expected:,} table={after_export:,}"
            )
        if view_count != after_export:
            raise RuntimeError(
                f"View mismatch: export={after_export:,} view={view_count:,}"
            )

        cur.execute(
            """
            SELECT TOP 5 ProjectID, Name, PartNumber, Manufacturer
            FROM dbo.vw_ReferenceNormalized
            ORDER BY ProjectID, Name
            """
        )
        print("\nSAMPLE_ROWS (top 5 from vw_ReferenceNormalized):")
        for row in cur.fetchall():
            print("  " + " | ".join("" if v is None else str(v) for v in row))

    total_time = time.time() - t_start
    print("\n" + "=" * 65)
    print(f" AFTER_RAW_COUNT     = {after_raw:,}")
    print(f" AFTER_EXPORT_COUNT  = {after_export:,}")
    print(f" VIEW_COUNT          = {view_count:,}")
    print(f" TOTAL_TIME          = {total_time:.1f}s")
    print(" STATUS              = ✅ COMPLETE")
    print("=" * 65)


if __name__ == "__main__":
    main()
