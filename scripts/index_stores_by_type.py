#!/usr/bin/env python
"""Index stores by survey type - split the reference workbook into individual store CSVs.

OPTIMIZED VERSION - uses vectorized pandas operations for 1M+ row datasets.
NOW PROCESSES ALL SHEETS!
INCLUDES CCTV DATABASE WORKSHEET PROCESSING!

This script:
1. Loads ALL sheets from Camera&Alarm Ref Data workbook
2. Extracts unique store numbers (SelectedSiteID)  
3. For each store, splits rows into CCTV vs FA/Intrusion:
   - CCTV: Abbreviated Name AND Description are EMPTY
   - FA/Intrusion: Abbreviated Name OR Description have CONTENT
4. Writes individual CSVs per store per type
5. Removes SelectedSiteID and Staging Site columns
6. Applies CCTV Database Worksheet structure:
   - Corrects headers (Abbreviated Names, MAC Address)
   - Populates Device ID (New0001 format)
   - Populates Device, Video Surveillance, Fixed Camera
   - Populates coordinate anchor (10.00, 30.00)
   - Preserves Project ID and Plan ID

Output folders:
- CCTV: Master Excel Pathing/CCTV STORES DATA - Survey/
- FA/Intrusion: Master Excel Pathing/FA&Intrusion STORES DATA - Survey/
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# =============================================================================
# PATHS
# =============================================================================
WORKBOOK_PATH = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Microsoft Teams Chat Files\Camera&Alarm Ref Data 1.xlsx")

CCTV_OUTPUT_DIR = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CCTV STORES DATA - Survey")
FA_INTRUSION_OUTPUT_DIR = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\FA&Intrusion STORES DATA - Survey")

# Columns to remove from exports
COLUMNS_TO_REMOVE = {"SelectedSiteID", "Staging Site"}

# =============================================================================
# CCTV DATABASE WORKSHEET CONFIGURATION
# =============================================================================
# Column indices after SelectedSiteID and Staging Site removal (0-based)
COL_PROJECT_ID = 0       # A - DO NOT OVERWRITE
COL_PLAN_ID = 1          # B - DO NOT OVERWRITE
COL_DEVICE_ID = 4        # E - Sequential New0001 format
COL_NAME = 5             # F - Used to detect valid device rows
COL_ABBREVIATED = 6      # G - Header rename: "Abbreviated Names"
COL_DEVICE_TASK = 7      # H - Populate: "Device"
COL_SYSTEM_TYPE = 8      # I - Populate: "Video Surveillance"
COL_DEVICE_TYPE = 9      # J - Populate: "Fixed Camera"
COL_MAC_ADDRESS = 26     # AA - Header rename: "MAC Address"
COL_COORDINATES = 53     # BB - Populate: "(10.00, 30.00)"

# Header corrections (old -> new)
HEADER_CORRECTIONS = {
    "Abreviated ": "Abbreviated Names",
    "Abreviated": "Abbreviated Names",
    "Abbreviated Name": "Abbreviated Names",
    "AbbreviatedName": "Abbreviated Names",
    "MACAddress": "MAC Address",
    "Mac Address": "MAC Address",
    "macaddress": "MAC Address",
}

# Required values for CCTV device rows
DEVICE_TASK_VALUE = "Device"
SYSTEM_TYPE_VALUE = "Video Surveillance"
DEVICE_TYPE_VALUE = "Fixed Camera"
COORDINATES_VALUE = "(10.00, 30.00)"  # Will be quoted in CSV output


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def clean_site_id(site_id) -> str:
    """Normalize site ID to a clean string for filenames."""
    if pd.isna(site_id):
        return ""
    s = str(site_id).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Find a column by trying multiple candidate names (case-insensitive, strip whitespace)."""
    col_map = {col.strip().lower(): col for col in df.columns}
    for candidate in candidates:
        actual = col_map.get(candidate.strip().lower())
        if actual is not None:
            return actual
    return None


def format_device_id(seq_num: int) -> str:
    """Format device ID as New0001, New0002, etc."""
    return f"New{seq_num:04d}"


def is_valid_device_row(row: list[str], name_col: int) -> bool:
    """Check if a row is a valid device row (has content in Name column)."""
    if len(row) <= name_col:
        return False
    name = row[name_col].strip() if row[name_col] else ""
    return bool(name)


def is_blank_row(row: list[str]) -> bool:
    """Check if entire row is blank/empty."""
    return all(not cell.strip() for cell in row)


def ensure_row_length(row: list[str], min_length: int) -> list[str]:
    """Extend row with empty strings if needed."""
    while len(row) < min_length:
        row.append("")
    return row


def csv_escape(value: str) -> str:
    """Escape a value for CSV output (quote if contains comma or quotes)."""
    if ',' in value or '"' in value or '\n' in value:
        # Escape internal quotes by doubling them
        value = value.replace('"', '""')
        return f'"{value}"'
    return value


def row_to_csv_line(row: list[str]) -> str:
    """Convert a row to a properly escaped CSV line."""
    return ','.join(csv_escape(cell) for cell in row)


# =============================================================================
# POST-PROCESSING: REMOVE COLUMNS
# =============================================================================
def remove_columns_from_file(filepath: Path) -> bool:
    """Remove specified columns from a CSV file. Returns True if modified."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        
        if not lines:
            return False
        
        header = lines[0].rstrip("\r\n").split(",")
        indices_to_remove = {i for i, col in enumerate(header) if col.strip() in COLUMNS_TO_REMOVE}
        
        if not indices_to_remove:
            return False
        
        new_lines = []
        for line in lines:
            parts = line.rstrip("\r\n").split(",")
            new_parts = [p for i, p in enumerate(parts) if i not in indices_to_remove]
            new_lines.append(",".join(new_parts) + "\n")
        
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            f.writelines(new_lines)
        
        return True
    except Exception:
        return False


# =============================================================================
# POST-PROCESSING: CCTV DATABASE WORKSHEET STRUCTURE
# =============================================================================
def apply_cctv_worksheet_structure(filepath: Path) -> dict:
    """Apply CCTV Database Worksheet structure to a CSV file.
    
    Returns dict with processing stats.
    """
    stats = {"devices_numbered": 0, "headers_corrected": 0, "error": None}
    
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        
        if not lines:
            return stats
        
        rows = [line.rstrip("\r\n").split(",") for line in lines]
        
        # --- Correct header names ---
        header = rows[0]
        header = ensure_row_length(header, COL_COORDINATES + 1)
        
        for i, col_name in enumerate(header):
            col_stripped = col_name.strip()
            if col_stripped in HEADER_CORRECTIONS:
                header[i] = HEADER_CORRECTIONS[col_stripped]
                stats["headers_corrected"] += 1
        
        rows[0] = header
        
        # --- Process device rows ---
        device_seq = 0
        
        for row_idx in range(1, len(rows)):
            row = rows[row_idx]
            
            if is_blank_row(row):
                continue
            
            if not is_valid_device_row(row, COL_NAME):
                continue
            
            row = ensure_row_length(row, COL_COORDINATES + 1)
            
            # Populate required fields
            device_seq += 1
            row[COL_DEVICE_ID] = format_device_id(device_seq)
            row[COL_DEVICE_TASK] = DEVICE_TASK_VALUE
            row[COL_SYSTEM_TYPE] = SYSTEM_TYPE_VALUE
            row[COL_DEVICE_TYPE] = DEVICE_TYPE_VALUE
            row[COL_COORDINATES] = COORDINATES_VALUE
            
            stats["devices_numbered"] += 1
            rows[row_idx] = row
        
        # Write back with proper CSV escaping
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            for row in rows:
                f.write(row_to_csv_line(row) + "\n")
        
    except Exception as e:
        stats["error"] = str(e)
    
    return stats


# =============================================================================
# MAIN
# =============================================================================
def main() -> int:
    log.info("=" * 70)
    log.info("Store Indexing Script - OPTIMIZED for 1M+ rows")
    log.info("Processing ALL SHEETS + CCTV Worksheet Structure")
    log.info("=" * 70)
    
    if not WORKBOOK_PATH.exists():
        log.error("Workbook not found: %s", WORKBOOK_PATH)
        return 1
    
    CCTV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FA_INTRUSION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # =========================================================================
    # PHASE 1: Load and split data
    # =========================================================================
    log.info("PHASE 1: Loading and splitting data")
    log.info("-" * 70)
    
    log.info("Loading workbook: %s", WORKBOOK_PATH.name)
    xl = pd.ExcelFile(WORKBOOK_PATH, engine="calamine")
    sheet_names = xl.sheet_names
    log.info("Found %d sheets: %s", len(sheet_names), sheet_names)
    
    all_dfs = []
    for sheet_name in sheet_names:
        log.info("Loading sheet: %s ...", sheet_name)
        df = pd.read_excel(xl, sheet_name=sheet_name, dtype=str)
        log.info("  -> %d rows, %d columns", len(df), len(df.columns))
        all_dfs.append(df)
    
    df = pd.concat(all_dfs, ignore_index=True)
    log.info("Combined total: %d rows", len(df))
    
    # Find required columns
    site_col = find_column(df, ["SelectedSiteID", "Selected Site ID", "SiteID", "Site ID", "Site Number"])
    if site_col is None:
        log.error("Could not find site ID column. Available: %s", list(df.columns)[:20])
        return 1
    log.info("Site ID column: %s", site_col)
    
    abbrev_col = find_column(df, ["Abreviated ", "Abreviated", "Abbreviated Name", "AbbreviatedName", "Abbreviated"])
    desc_col = find_column(df, ["Description"])
    
    if abbrev_col:
        log.info("Abbreviated column: '%s'", abbrev_col)
    if desc_col:
        log.info("Description column: '%s'", desc_col)
    
    # Vectorized split
    log.info("Computing CCTV/FA split masks (vectorized)...")
    
    def col_has_content(col_name: str | None) -> pd.Series:
        if col_name is None or col_name not in df.columns:
            return pd.Series([False] * len(df), index=df.index)
        return df[col_name].fillna("").astype(str).str.strip().ne("")
    
    abbrev_has_content = col_has_content(abbrev_col)
    desc_has_content = col_has_content(desc_col)
    
    cctv_mask = ~abbrev_has_content & ~desc_has_content
    fa_mask = abbrev_has_content | desc_has_content
    
    log.info("Total CCTV rows: %d", cctv_mask.sum())
    log.info("Total FA/Intrusion rows: %d", fa_mask.sum())
    
    # Clean site IDs
    log.info("Normalizing site IDs...")
    df["__clean_site__"] = df[site_col].apply(clean_site_id)
    
    unique_sites = df["__clean_site__"].loc[df["__clean_site__"].ne("")].unique()
    unique_sites = sorted(unique_sites)
    
    log.info("Found %d unique stores to process", len(unique_sites))
    
    # Pre-split dataframes
    cctv_df = df[cctv_mask].copy()
    fa_df = df[fa_mask].copy()
    
    log.info("Grouping by site...")
    cctv_grouped = cctv_df.groupby("__clean_site__", sort=False)
    fa_grouped = fa_df.groupby("__clean_site__", sort=False)
    
    cctv_groups = {name: group.drop(columns=["__clean_site__"]) for name, group in cctv_grouped}
    fa_groups = {name: group.drop(columns=["__clean_site__"]) for name, group in fa_grouped}
    
    # =========================================================================
    # PHASE 2: Write CSV files
    # =========================================================================
    log.info("-" * 70)
    log.info("PHASE 2: Writing individual store CSVs")
    log.info("-" * 70)
    
    cctv_files = []
    fa_files = 0
    cctv_total_rows = 0
    fa_total_rows = 0
    
    for i, site_id in enumerate(unique_sites, 1):
        if i % 500 == 0:
            log.info("Progress: %d / %d stores...", i, len(unique_sites))
        
        if site_id in cctv_groups:
            site_cctv = cctv_groups[site_id]
            if not site_cctv.empty:
                cctv_path = CCTV_OUTPUT_DIR / f"Store_{site_id}_CCTV.csv"
                site_cctv.to_csv(cctv_path, index=False)
                cctv_files.append(cctv_path)
                cctv_total_rows += len(site_cctv)
        
        if site_id in fa_groups:
            site_fa = fa_groups[site_id]
            if not site_fa.empty:
                fa_path = FA_INTRUSION_OUTPUT_DIR / f"Store_{site_id}_FA_Intrusion.csv"
                site_fa.to_csv(fa_path, index=False)
                fa_files += 1
                fa_total_rows += len(site_fa)
    
    log.info("CCTV files created: %d", len(cctv_files))
    log.info("FA/Intrusion files created: %d", fa_files)
    
    # =========================================================================
    # PHASE 3: Remove unwanted columns
    # =========================================================================
    log.info("-" * 70)
    log.info("PHASE 3: Removing SelectedSiteID and Staging Site columns")
    log.info("-" * 70)
    
    all_files = list(CCTV_OUTPUT_DIR.glob("*.csv")) + list(FA_INTRUSION_OUTPUT_DIR.glob("*.csv"))
    for i, filepath in enumerate(all_files):
        if (i + 1) % 1000 == 0:
            log.info("Removing columns: %d / %d files...", i + 1, len(all_files))
        remove_columns_from_file(filepath)
    
    log.info("Column removal complete")
    
    # =========================================================================
    # PHASE 4: Apply CCTV Database Worksheet structure (CCTV only)
    # =========================================================================
    log.info("-" * 70)
    log.info("PHASE 4: Applying CCTV Database Worksheet structure")
    log.info("-" * 70)
    log.info("  - Header corrections: Abbreviated Names, MAC Address")
    log.info("  - Column E: Device ID (New0001 format)")
    log.info("  - Column H: Device")
    log.info("  - Column I: Video Surveillance")
    log.info("  - Column J: Fixed Camera")
    log.info("  - Column BB: (10.00, 30.00)")
    log.info("  - Project ID and Plan ID: PRESERVED")
    
    cctv_file_list = list(CCTV_OUTPUT_DIR.glob("*.csv"))
    total_devices = 0
    total_headers = 0
    
    for i, filepath in enumerate(cctv_file_list):
        if (i + 1) % 500 == 0:
            log.info("Processing CCTV worksheets: %d / %d files...", i + 1, len(cctv_file_list))
        stats = apply_cctv_worksheet_structure(filepath)
        total_devices += stats["devices_numbered"]
        total_headers += stats["headers_corrected"]
    
    log.info("CCTV worksheet processing complete")
    log.info("  Devices numbered: %d", total_devices)
    log.info("  Headers corrected: %d", total_headers)
    
    # =========================================================================
    # FINAL REPORT
    # =========================================================================
    log.info("=" * 70)
    log.info("INDEXING COMPLETE - ALL PHASES DONE")
    log.info("=" * 70)
    log.info("Sheets processed: %s", sheet_names)
    log.info("Total unique stores: %d", len(unique_sites))
    log.info("-" * 70)
    log.info("CCTV:")
    log.info("  Files created: %d", len(cctv_files))
    log.info("  Total rows: %d", cctv_total_rows)
    log.info("  Devices numbered: %d", total_devices)
    log.info("  Output: %s", CCTV_OUTPUT_DIR)
    log.info("-" * 70)
    log.info("FA/Intrusion:")
    log.info("  Files created: %d", fa_files)
    log.info("  Total rows: %d", fa_total_rows)
    log.info("  Output: %s", FA_INTRUSION_OUTPUT_DIR)
    log.info("=" * 70)
    log.info("CCTV Worksheet Structure Applied:")
    log.info("  [x] Column E: Device ID (New0001 format)")
    log.info("  [x] Column H: Device")
    log.info("  [x] Column I: Video Surveillance")
    log.info("  [x] Column J: Fixed Camera")
    log.info("  [x] Column BB: (10.00, 30.00)")
    log.info("  [x] Headers: Abbreviated Names, MAC Address")
    log.info("  [x] Project ID and Plan ID: NOT overwritten")
    log.info("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
