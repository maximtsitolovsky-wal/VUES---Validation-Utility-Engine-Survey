"""
Scout Completion Sync — Airtable → Excel Status Tracker (COM Version)
======================================================================
Uses Windows COM automation to safely update Excel files with data models.

This version controls Excel like a human would, preserving:
  - Data models / Power Pivot
  - VBA macros
  - Complex formulas
  - All Excel features

Mapping:
  Airtable "Site Number"    → Excel "Store Number"
  Airtable "Complete?"      → Excel "Completed Scout" (True/False)
  When marking complete     → Excel "Confirmed by" = "code puppy (timestamp)"

Schedule: Mon-Fri 10:00 AM and 3:00 PM via Windows Task Scheduler.
"""
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import win32com.client

# ── Config ────────────────────────────────────────────────────────────────────
API_KEY   = "patPR0WWxXCE0loRO.d18126548ad25b8aaf9fd43e2ac69479b1378e46d7f8c6efbdd88f7197a4d495"
BASE_ID   = "appAwgaX89x0JxG3Z"
TABLE_ID  = "tblC4o9AvVulyxFMk"

AIRTABLE_SITE_COL = "Site Number"
AIRTABLE_COMPLETE_COL = "Complete?"
AIRTABLE_VENDOR_COL = "Vendor Parent Company"
AIRTABLE_SURVEYOR_COL = "Surveyor Name"

EXCEL_PATH = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Documents\BaselinePrinter\ScoutSurveyLab.xlsm")
EXCEL_SHEET_NAME = "Scout Map Data"
EXCEL_OUTLIER_SHEET_NAME = "Outlier Scout"
EXCEL_STORE_COL = "Store Number"
EXCEL_COMPLETED_COL = "Completed Scout"
EXCEL_CONFIRMED_BY_COL = "Confirmed by"

LOG_FILE = Path(__file__).resolve().parents[1] / "logs" / "scout_completion_sync.log"

AIRTABLE_URL = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
AIRTABLE_HDR = {"Authorization": f"Bearer {API_KEY}"}


# ── Helpers ───────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    """Log to console and file."""
    print(msg, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} {msg}\n")
    except Exception:
        pass


def fetch_airtable_records() -> list[dict]:
    """Fetch all records from Scout Airtable with pagination."""
    records, params = [], {}
    while True:
        resp = requests.get(AIRTABLE_URL, headers=AIRTABLE_HDR, params=params, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        records.extend(body.get("records", []))
        offset = body.get("offset")
        if not offset:
            break
        params = {"offset": offset}
        time.sleep(0.2)
    return records


def parse_site_number(value) -> str:
    """Normalize site/store number to string for matching."""
    if value is None:
        return ""
    return str(value).strip()


def is_complete(complete_value) -> bool:
    """Check if Airtable 'Complete?' field is truthy."""
    if complete_value is None:
        return False
    if isinstance(complete_value, bool):
        return complete_value
    if isinstance(complete_value, str):
        return complete_value.lower() in ("true", "yes", "1", "✓", "x")
    return bool(complete_value)


def find_column_index(header_row, column_name: str) -> int:
    """Find column index by header name. Returns 0 if not found."""
    for col_idx in range(1, header_row.Columns.Count + 1):
        cell_val = header_row.Cells(1, col_idx).Value
        if cell_val and str(cell_val).strip() == column_name:
            return col_idx
    return 0


def sync_completion_status() -> tuple[int, int, int]:
    """
    Sync completion status from Airtable to Excel using COM automation.
    
    Returns:
        (updated, skipped, errors) counts
    """
    log("[*] Fetching records from Airtable...")
    airtable_records = fetch_airtable_records()
    log(f"[OK] Fetched {len(airtable_records)} records from Airtable")

    # Build completion map
    completion_map = {}
    for rec in airtable_records:
        fields = rec.get("fields", {})
        site_num = parse_site_number(fields.get(AIRTABLE_SITE_COL))
        complete = is_complete(fields.get(AIRTABLE_COMPLETE_COL))
        vendor = fields.get(AIRTABLE_VENDOR_COL, "")
        surveyor = fields.get(AIRTABLE_SURVEYOR_COL, "")
        if site_num:
            completion_map[site_num] = {
                "complete": complete,
                "vendor": vendor,
                "surveyor": surveyor
            }

    log(f"[*] Built completion map with {len(completion_map)} sites")
    log(f"[*] Sites marked complete: {sum(1 for v in completion_map.values() if v['complete'])}")

    # Open Excel via COM
    if not EXCEL_PATH.exists():
        log(f"[ERROR] Excel file not found: {EXCEL_PATH}")
        return 0, 0, 1

    log(f"[*] Opening Excel via COM: {EXCEL_PATH.name}...")
    
    excel = None
    wb = None
    try:
        # Start Excel application
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = False  # Hidden mode
        excel.DisplayAlerts = False  # Suppress prompts
        
        # Open workbook
        wb = excel.Workbooks.Open(str(EXCEL_PATH.absolute()))
        log(f"[OK] Workbook opened successfully")
        
        # Get Scout Map Data sheet
        ws = None
        for sheet in wb.Sheets:
            if sheet.Name == EXCEL_SHEET_NAME:
                ws = sheet
                break
        
        if ws is None:
            log(f"[ERROR] Sheet '{EXCEL_SHEET_NAME}' not found")
            log(f"        Available sheets: {', '.join([s.Name for s in wb.Sheets])}")
            return 0, 0, 1
        
        log(f"[*] Using sheet: {ws.Name}")
        
        # Get or create Outlier Scout sheet
        outlier_ws = None
        for sheet in wb.Sheets:
            if sheet.Name == EXCEL_OUTLIER_SHEET_NAME:
                outlier_ws = sheet
                break
        
        if outlier_ws is None:
            log(f"[*] Creating new sheet: {EXCEL_OUTLIER_SHEET_NAME}")
            outlier_ws = wb.Sheets.Add()
            outlier_ws.Name = EXCEL_OUTLIER_SHEET_NAME
            outlier_ws.Cells(1, 1).Value = "Site Number"
            outlier_ws.Cells(1, 2).Value = "Vendor Parent Company"
            outlier_ws.Cells(1, 3).Value = "Surveyor Name"
        else:
            log(f"[*] Found existing sheet: {EXCEL_OUTLIER_SHEET_NAME}")
        
        # Find header row and columns in Scout Map Data
        header_row_idx = 1
        store_col_idx = find_column_index(ws.Rows(header_row_idx), EXCEL_STORE_COL)
        completed_col_idx = find_column_index(ws.Rows(header_row_idx), EXCEL_COMPLETED_COL)
        confirmed_by_col_idx = find_column_index(ws.Rows(header_row_idx), EXCEL_CONFIRMED_BY_COL)
        
        if not all([store_col_idx, completed_col_idx]):
            log(f"[ERROR] Required columns not found. Store={store_col_idx}, Completed={completed_col_idx}")
            return 0, 0, 1
        
        log(f"[OK] Found headers at row {header_row_idx}: Store col={store_col_idx}, Completed col={completed_col_idx}, Confirmed by col={confirmed_by_col_idx}")
        
        # Build set of existing stores
        existing_stores = set()
        last_row = ws.UsedRange.Rows.Count
        
        for row_idx in range(header_row_idx + 1, last_row + 1):
            store_val = ws.Cells(row_idx, store_col_idx).Value
            store_num = parse_site_number(store_val)
            if store_num:
                existing_stores.add(store_num)
        
        log(f"[*] Found {len(existing_stores)} existing stores in '{EXCEL_SHEET_NAME}'")
        
        # Track outliers
        outliers = []
        for site_num, data in completion_map.items():
            if site_num not in existing_stores:
                outliers.append({
                    "site_number": site_num,
                    "vendor": data["vendor"],
                    "surveyor": data["surveyor"]
                })
        
        if outliers:
            log(f"[*] Found {len(outliers)} outlier site(s) not in Scout Map Data")
        
        # Process data rows
        updated = 0
        already_complete = 0
        skipped = 0
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for row_idx in range(header_row_idx + 1, last_row + 1):
            store_val = ws.Cells(row_idx, store_col_idx).Value
            store_num = parse_site_number(store_val)
            
            if not store_num:
                continue
            
            if store_num not in completion_map:
                skipped += 1
                continue
            
            site_data = completion_map[store_num]
            airtable_complete = site_data["complete"]
            current_value = ws.Cells(row_idx, completed_col_idx).Value
            
            # Check if already complete
            current_complete = False
            if isinstance(current_value, bool):
                current_complete = current_value
            elif isinstance(current_value, str):
                current_complete = current_value.lower() in ("true", "yes", "1", "✓", "x")
            
            # Update if Airtable says complete but Excel doesn't
            if airtable_complete and not current_complete:
                ws.Cells(row_idx, completed_col_idx).Value = True
                
                if confirmed_by_col_idx:
                    ws.Cells(row_idx, confirmed_by_col_idx).Value = f"code puppy ({now_str})"
                
                log(f"   [UPDATE] Store {store_num}: Completed Scout -> True")
                updated += 1
            elif airtable_complete and current_complete:
                already_complete += 1
            else:
                skipped += 1
        
        # Write outliers
        outliers_added = 0
        if outliers:
            # Get existing outliers
            existing_outliers = set()
            outlier_last_row = outlier_ws.UsedRange.Rows.Count
            
            for row_idx in range(2, outlier_last_row + 1):
                site = parse_site_number(outlier_ws.Cells(row_idx, 1).Value)
                if site:
                    existing_outliers.add(site)
            
            # Add new outliers
            next_row = outlier_last_row + 1
            for outlier in outliers:
                if outlier["site_number"] not in existing_outliers:
                    outlier_ws.Cells(next_row, 1).Value = outlier["site_number"]
                    outlier_ws.Cells(next_row, 2).Value = outlier["vendor"]
                    outlier_ws.Cells(next_row, 3).Value = outlier["surveyor"]
                    log(f"   [OUTLIER] Added site {outlier['site_number']} to Outlier Scout")
                    next_row += 1
                    outliers_added += 1
            
            if outliers_added > 0:
                log(f"[*] Added {outliers_added} new outliers to '{EXCEL_OUTLIER_SHEET_NAME}'")
        
        # Summary
        total_processed = updated + already_complete + len(outliers)
        log(f"\n[SUMMARY] All {len(completion_map)} Airtable submissions accounted for:")
        log(f"  - {updated} stores UPDATED (False -> True)")
        log(f"  - {already_complete} stores ALREADY COMPLETE (no change needed)")
        log(f"  - {len(outliers)} stores are OUTLIERS (not in Scout Map Data)")
        log(f"  - Total: {updated} + {already_complete} + {len(outliers)} = {total_processed}")
        
        # Save and close
        if updated > 0 or outliers_added > 0:
            log(f"[*] Saving changes to Excel...")
            wb.Save()
            log(f"[OK] Saved {updated} updates + {outliers_added} outliers to {EXCEL_PATH.name}")
        else:
            log("[*] No updates needed - Excel already in sync")
        
        return updated, skipped, 0
        
    except Exception as e:
        log(f"[ERROR] COM automation failed: {e}")
        import traceback
        log(traceback.format_exc())
        return 0, 0, 1
        
    finally:
        # Clean up COM objects
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


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    log("=" * 80)
    log(f"[START] Scout Completion Sync (COM) — {datetime.now().isoformat()}")
    log("=" * 80)

    try:
        updated, skipped, errors = sync_completion_status()
        log("\n" + "=" * 80)
        log(f"[DONE] Updated={updated}  Skipped={skipped}  Errors={errors}")
        log("=" * 80)
        
        sys.exit(1 if errors > 0 else 0)
    
    except Exception as exc:
        log(f"[FATAL] {exc}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
