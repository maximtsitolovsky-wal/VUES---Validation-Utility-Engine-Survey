"""
scout_completion_sync_worker.py — Syncs Scout completion status as a daemon thread.

Runs as a daemon thread inside the main SiteOwlQA process.
On startup: syncs immediately (60s delay so the pipeline warms up first).
Then: re-syncs every SYNC_INTERVAL_HOURS (6 hours) continuously.

Uses Windows COM automation to safely update Excel files with data models.
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path

import requests
import win32com.client

log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
_API_KEY   = os.getenv("SCOUT_AIRTABLE_API_KEY", "")
_BASE_ID   = os.getenv("SCOUT_AIRTABLE_BASE_ID", "appAwgaX89x0JxG3Z")
_TABLE_ID  = os.getenv("SCOUT_AIRTABLE_TABLE_ID", "tblC4o9AvVulyxFMk")

_AIRTABLE_SITE_COL = "Site Number"
_AIRTABLE_COMPLETE_COL = "Complete?"
_AIRTABLE_VENDOR_COL = "Vendor Parent Company"
_AIRTABLE_SURVEYOR_COL = "Surveyor Name"

_EXCEL_PATH = Path(
    r"C:\Users\vn59j7j\OneDrive - Walmart Inc"
    r"\Documents\BaselinePrinter\ScoutSurveyLab.xlsm"
)
_EXCEL_SHEET_NAME = "Scout Map Data"
_EXCEL_OUTLIER_SHEET_NAME = "Outlier Scout"
_EXCEL_STORE_COL = "Store Number"
_EXCEL_COMPLETED_COL = "Completed Scout"
_EXCEL_CONFIRMED_BY_COL = "Confirmed by"

_AIRTABLE_URL = f"https://api.airtable.com/v0/{_BASE_ID}/{_TABLE_ID}"
_AIRTABLE_HDR = {"Authorization": f"Bearer {_API_KEY}"}

STARTUP_DELAY_SECONDS = 60          # wait for pipeline to warm up first
SYNC_INTERVAL_HOURS   = 6          # re-sync every 6 hours while running


# ── Helpers ───────────────────────────────────────────────────────────────────
def _fetch_records() -> list[dict]:
    """Fetch all records from Scout Airtable with pagination."""
    records, params = [], {}
    while True:
        resp = requests.get(_AIRTABLE_URL, headers=_AIRTABLE_HDR, params=params, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        records.extend(body.get("records", []))
        offset = body.get("offset")
        if not offset:
            break
        params = {"offset": offset}
        time.sleep(0.2)
    return records


def _parse_site_number(value) -> str:
    """Normalize site/store number for matching.
    
    Handles vendor inconsistencies:
      - "0038" -> "38"
      - "Store 38" -> "38"
      - "  0038  " -> "38"
    """
    if value is None:
        return ""
    
    s = str(value).strip()
    match = re.search(r'\\d+', s)
    if match:
        num_str = match.group(0).lstrip('0')
        return num_str if num_str else "0"
    
    return s


def _is_complete(complete_value) -> bool:
    """Check if Airtable 'Complete?' field is truthy."""
    if complete_value is None:
        return False
    if isinstance(complete_value, bool):
        return complete_value
    if isinstance(complete_value, str):
        return complete_value.lower() in ("true", "yes", "1", "✓", "x")
    return bool(complete_value)


def _find_column_index(worksheet, header_row_idx: int, column_name: str, max_cols: int = 100) -> int:
    """Find column index by header name. Handles newlines in headers."""
    search_normalized = " ".join(column_name.split())
    
    for col_idx in range(1, max_cols + 1):
        try:
            cell_val = worksheet.Cells(header_row_idx, col_idx).Value
            if cell_val:
                cell_normalized = " ".join(str(cell_val).split())
                if cell_normalized == search_normalized:
                    return col_idx
        except:
            break
    return 0


def _run_sync() -> tuple[int, int, int]:
    """Fetch Airtable records and update Excel via COM automation.
    
    Returns (updated, skipped, errors) counts.
    """
    log.info("ScoutCompletionSync: starting sync at %s", datetime.now().isoformat())
    
    # Fetch from Airtable
    records = _fetch_records()
    log.info("ScoutCompletionSync: fetched %d record(s) from Airtable.", len(records))
    
    # Build completion map
    completion_map = {}
    for rec in records:
        fields = rec.get("fields", {})
        site_num = _parse_site_number(fields.get(_AIRTABLE_SITE_COL))
        complete = _is_complete(fields.get(_AIRTABLE_COMPLETE_COL))
        vendor = fields.get(_AIRTABLE_VENDOR_COL, "")
        surveyor = fields.get(_AIRTABLE_SURVEYOR_COL, "")
        if site_num:
            completion_map[site_num] = {
                "complete": complete,
                "vendor": vendor,
                "surveyor": surveyor
            }
    
    log.info("ScoutCompletionSync: built map with %d sites, %d complete",
             len(completion_map),
             sum(1 for v in completion_map.values() if v["complete"]))
    
    if not _EXCEL_PATH.exists():
        log.error("ScoutCompletionSync: Excel file not found: %s", _EXCEL_PATH)
        return 0, 0, 1
    
    excel = None
    wb = None
    updated = 0
    already_complete = 0
    skipped = 0
    
    try:
        # Open Excel via COM
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        
        wb = excel.Workbooks.Open(str(_EXCEL_PATH.absolute()))
        
        # Get Scout Map Data sheet
        ws = None
        for sheet in wb.Sheets:
            if sheet.Name == _EXCEL_SHEET_NAME:
                ws = sheet
                break
        
        if ws is None:
            log.error("ScoutCompletionSync: sheet '%s' not found", _EXCEL_SHEET_NAME)
            return 0, 0, 1
        
        # Get or create Outlier Scout sheet
        outlier_ws = None
        for sheet in wb.Sheets:
            if sheet.Name == _EXCEL_OUTLIER_SHEET_NAME:
                outlier_ws = sheet
                break
        
        if outlier_ws is None:
            log.info("ScoutCompletionSync: creating '%s' sheet", _EXCEL_OUTLIER_SHEET_NAME)
            outlier_ws = wb.Sheets.Add()
            outlier_ws.Name = _EXCEL_OUTLIER_SHEET_NAME
            outlier_ws.Cells(1, 1).Value = "Site Number"
            outlier_ws.Cells(1, 2).Value = "Vendor Parent Company"
            outlier_ws.Cells(1, 3).Value = "Surveyor Name"
        
        # Find columns
        header_row_idx = 1
        store_col_idx = _find_column_index(ws, header_row_idx, _EXCEL_STORE_COL)
        completed_col_idx = _find_column_index(ws, header_row_idx, _EXCEL_COMPLETED_COL)
        confirmed_by_col_idx = _find_column_index(ws, header_row_idx, _EXCEL_CONFIRMED_BY_COL)
        
        if not all([store_col_idx, completed_col_idx]):
            log.error("ScoutCompletionSync: columns not found. Store=%d, Completed=%d",
                     store_col_idx, completed_col_idx)
            return 0, 0, 1
        
        # Build set of existing stores
        existing_stores = set()
        last_row = ws.UsedRange.Rows.Count
        
        for row_idx in range(header_row_idx + 1, last_row + 1):
            store_val = ws.Cells(row_idx, store_col_idx).Value
            store_num = _parse_site_number(store_val)
            if store_num:
                existing_stores.add(store_num)
        
        # Track outliers
        outliers = []
        for site_num, data in completion_map.items():
            if site_num not in existing_stores:
                outliers.append({
                    "site_number": site_num,
                    "vendor": data["vendor"],
                    "surveyor": data["surveyor"]
                })
        
        # Process data rows
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for row_idx in range(header_row_idx + 1, last_row + 1):
            store_val = ws.Cells(row_idx, store_col_idx).Value
            store_num = _parse_site_number(store_val)
            
            if not store_num or store_num not in completion_map:
                skipped += 1
                continue
            
            site_data = completion_map[store_num]
            airtable_complete = site_data["complete"]
            current_value = ws.Cells(row_idx, completed_col_idx).Value
            
            current_complete = False
            if isinstance(current_value, bool):
                current_complete = current_value
            elif isinstance(current_value, str):
                current_complete = current_value.lower() in ("true", "yes", "1", "✓", "x")
            
            if airtable_complete and not current_complete:
                ws.Cells(row_idx, completed_col_idx).Value = True
                if confirmed_by_col_idx:
                    ws.Cells(row_idx, confirmed_by_col_idx).Value = f"code puppy ({now_str})"
                updated += 1
            elif airtable_complete and current_complete:
                already_complete += 1
            else:
                skipped += 1
        
        # Write outliers
        outliers_added = 0
        if outliers:
            existing_outliers = set()
            outlier_last_row = outlier_ws.UsedRange.Rows.Count
            
            for row_idx in range(2, outlier_last_row + 1):
                site = _parse_site_number(outlier_ws.Cells(row_idx, 1).Value)
                if site:
                    existing_outliers.add(site)
            
            next_row = outlier_last_row + 1
            for outlier in outliers:
                if outlier["site_number"] not in existing_outliers:
                    outlier_ws.Cells(next_row, 1).Value = outlier["site_number"]
                    outlier_ws.Cells(next_row, 2).Value = outlier["vendor"]
                    outlier_ws.Cells(next_row, 3).Value = outlier["surveyor"]
                    next_row += 1
                    outliers_added += 1
        
        # Save if changes
        if updated > 0 or outliers_added > 0:
            wb.Save()
            log.info(
                "ScoutCompletionSync: saved %d updates + %d outliers. Summary: %d updated, %d already complete, %d outliers",
                updated, outliers_added, updated, already_complete, len(outliers)
            )
        else:
            log.info("ScoutCompletionSync: no updates needed - already in sync")
        
        return updated, skipped, 0
        
    except Exception as e:
        log.exception("ScoutCompletionSync: sync failed: %s", e)
        return 0, 0, 1
        
    finally:
        if wb:
            try:
                wb.Close(SaveChanges=False if updated == 0 else True)
            except:
                pass
        if excel:
            try:
                excel.Quit()
            except:
                pass


# ── Worker thread ─────────────────────────────────────────────────────────────
class ScoutCompletionSyncWorker(threading.Thread):
    """Daemon thread that syncs Scout completion status from Airtable to Excel.
    
    Lifecycle mirrors ScoutSyncWorker:
      - start() called in run_forever() alongside other workers
      - Waits STARTUP_DELAY_SECONDS on first run
      - Syncs immediately after delay
      - Then syncs every SYNC_INTERVAL_HOURS continuously
      - request_shutdown() + join() called in Ctrl-C handler
    """

    def __init__(self) -> None:
        super().__init__(daemon=True, name="scout-completion-sync")
        self._stop = threading.Event()

    def request_shutdown(self) -> None:
        log.info("ScoutCompletionSyncWorker: shutdown requested.")
        self._stop.set()

    def run(self) -> None:
        log.info(
            "ScoutCompletionSyncWorker started. Initial delay %ds, then every %dh.",
            STARTUP_DELAY_SECONDS,
            SYNC_INTERVAL_HOURS,
        )

        # Wait for the pipeline to warm up before first sync
        if self._stop.wait(STARTUP_DELAY_SECONDS):
            return  # shutdown before first run — exit cleanly

        while True:
            log.info("ScoutCompletionSyncWorker: starting sync at %s", datetime.now().isoformat())
            try:
                updated, skipped, errors = _run_sync()
                log.info(
                    "ScoutCompletionSyncWorker: sync complete — Updated=%d Skipped=%d Errors=%d",
                    updated, skipped, errors,
                )
            except Exception as exc:  # noqa: BLE001
                log.exception("ScoutCompletionSyncWorker: sync failed (non-fatal): %s", exc)

            if self._stop.wait(SYNC_INTERVAL_HOURS * 3600):
                break  # shutdown event fired during sleep

        log.info("ScoutCompletionSyncWorker: stopped cleanly.")
