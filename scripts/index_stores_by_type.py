#!/usr/bin/env python
"""Index stores by survey type - split the reference workbook into individual store CSVs.

This script:
1. Loads the entire SQL DB MASTER workbook
2. Extracts unique store numbers (SelectedSiteID)
3. For each store, splits rows into CCTV vs FA/Intrusion:
   - CCTV: Abbreviated Name AND Description are EMPTY
   - FA/Intrusion: Abbreviated Name OR Description have CONTENT
4. Writes individual CSVs per store per type

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

# Paths - using Camera&Alarm Ref Data from Teams Chat Files (most recent local copy)
WORKBOOK_PATH = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Microsoft Teams Chat Files\Camera&Alarm Ref Data 1.xlsx")
SHEET_NAME = 0  # First sheet (index 0)
SITE_ID_COLUMN = "SelectedSiteID"  # Will try common aliases if not found

CCTV_OUTPUT_DIR = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CCTV STORES DATA - Survey")
FA_INTRUSION_OUTPUT_DIR = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\FA&Intrusion STORES DATA - Survey")

# The columns that determine CCTV vs FA/Intrusion split
# Based on VUES grading logic:
#   CCTV = rows WHERE Abbreviated Name AND Description are EMPTY
#   FA/Intrusion = rows WHERE Abbreviated Name OR Description have CONTENT
ABBREV_NAME_COL = "Abreviated_"  # BQ naming from the workbook
DESCRIPTION_COL = "Description"


def has_content(value) -> bool:
    """Check if a cell has meaningful content (not empty/whitespace/nan)."""
    if pd.isna(value):
        return False
    return bool(str(value).strip())


def is_cctv_row(row: pd.Series) -> bool:
    """CCTV row = Abbreviated Name AND Description are EMPTY."""
    return not has_content(row.get(ABBREV_NAME_COL, "")) and not has_content(row.get(DESCRIPTION_COL, ""))


def is_fa_intrusion_row(row: pd.Series) -> bool:
    """FA/Intrusion row = Abbreviated Name OR Description have CONTENT."""
    return has_content(row.get(ABBREV_NAME_COL, "")) or has_content(row.get(DESCRIPTION_COL, ""))


def clean_site_id(site_id) -> str:
    """Normalize site ID to a clean string for filenames."""
    if pd.isna(site_id):
        return ""
    s = str(site_id).strip()
    # Remove .0 suffix if it came from numeric conversion
    if s.endswith(".0"):
        s = s[:-2]
    return s


def main() -> int:
    log.info("=" * 70)
    log.info("Store Indexing Script - Splitting Reference Data by Survey Type")
    log.info("=" * 70)
    
    # Validate paths
    if not WORKBOOK_PATH.exists():
        log.error("Workbook not found: %s", WORKBOOK_PATH)
        return 1
    
    CCTV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FA_INTRUSION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load the workbook
    log.info("Loading workbook: %s", WORKBOOK_PATH.name)
    log.info("Sheet: %s", SHEET_NAME if isinstance(SHEET_NAME, str) else "<first sheet>")
    
    try:
        # Try calamine first (fast Rust engine), fallback to openpyxl
        try:
            df = pd.read_excel(
                WORKBOOK_PATH,
                sheet_name=SHEET_NAME,
                dtype=str,
                engine="calamine",
            )
            log.info("Using calamine engine (fast)")
        except Exception:
            df = pd.read_excel(
                WORKBOOK_PATH,
                sheet_name=SHEET_NAME,
                dtype=str,
                engine="openpyxl",
            )
            log.info("Using openpyxl engine")
    except Exception as e:
        log.error("Failed to load workbook: %s", e)
        return 1
    
    log.info("Loaded %d rows, %d columns", len(df), len(df.columns))
    log.info("Columns: %s", list(df.columns))
    
    # Find the site ID column (case-insensitive search)
    site_col = None
    for col in df.columns:
        if col.strip().lower() == SITE_ID_COLUMN.lower():
            site_col = col
            break
    
    if site_col is None:
        # Try common aliases
        aliases = ["SelectedSiteID", "Selected Site ID", "SiteID", "Site ID", "Site Number"]
        for alias in aliases:
            for col in df.columns:
                if col.strip().lower() == alias.lower():
                    site_col = col
                    log.info("Using alias '%s' for site ID column", col)
                    break
            if site_col:
                break
    
    if site_col is None:
        log.error("Could not find site ID column. Available: %s", list(df.columns))
        return 1
    
    # Find the split columns
    abbrev_col = None
    desc_col = None
    
    for col in df.columns:
        col_lower = col.strip().lower()
        if col_lower in ["abreviated_", "abbreviated name", "abbreviatedname"]:
            abbrev_col = col
        if col_lower == "description":
            desc_col = col
    
    if abbrev_col:
        log.info("Abbreviated Name column: %s", abbrev_col)
    else:
        log.warning("No Abbreviated Name column found - treating ALL rows as CCTV")
        
    if desc_col:
        log.info("Description column: %s", desc_col)
    else:
        log.warning("No Description column found - treating ALL rows as CCTV")
    
    # Get unique site IDs
    unique_sites = df[site_col].dropna().unique()
    unique_sites = [clean_site_id(s) for s in unique_sites if clean_site_id(s)]
    unique_sites = sorted(set(unique_sites))
    
    log.info("-" * 70)
    log.info("Found %d unique stores to process", len(unique_sites))
    log.info("-" * 70)
    
    # Stats
    cctv_files = 0
    fa_intrusion_files = 0
    cctv_total_rows = 0
    fa_intrusion_total_rows = 0
    empty_cctv = 0
    empty_fa = 0
    
    for i, site_id in enumerate(unique_sites, 1):
        if i % 100 == 0:
            log.info("Progress: %d / %d stores...", i, len(unique_sites))
        
        # Filter rows for this site
        site_mask = df[site_col].apply(lambda x: clean_site_id(x) == site_id)
        site_df = df[site_mask].copy()
        
        if site_df.empty:
            continue
        
        # Split into CCTV and FA/Intrusion
        if abbrev_col and desc_col:
            # Both columns exist - apply full split logic
            cctv_mask = site_df.apply(
                lambda row: (
                    not has_content(row.get(abbrev_col, "")) and 
                    not has_content(row.get(desc_col, ""))
                ),
                axis=1
            )
            fa_mask = site_df.apply(
                lambda row: (
                    has_content(row.get(abbrev_col, "")) or 
                    has_content(row.get(desc_col, ""))
                ),
                axis=1
            )
        elif abbrev_col:
            # Only abbreviated name column
            cctv_mask = site_df[abbrev_col].apply(lambda x: not has_content(x))
            fa_mask = site_df[abbrev_col].apply(has_content)
        elif desc_col:
            # Only description column
            cctv_mask = site_df[desc_col].apply(lambda x: not has_content(x))
            fa_mask = site_df[desc_col].apply(has_content)
        else:
            # No split columns - all goes to CCTV
            cctv_mask = pd.Series([True] * len(site_df), index=site_df.index)
            fa_mask = pd.Series([False] * len(site_df), index=site_df.index)
        
        cctv_df = site_df[cctv_mask]
        fa_df = site_df[fa_mask]
        
        # Write CCTV file (only if there are rows)
        if not cctv_df.empty:
            cctv_path = CCTV_OUTPUT_DIR / f"Store_{site_id}_CCTV.csv"
            cctv_df.to_csv(cctv_path, index=False)
            cctv_files += 1
            cctv_total_rows += len(cctv_df)
        else:
            empty_cctv += 1
        
        # Write FA/Intrusion file (only if there are rows)
        if not fa_df.empty:
            fa_path = FA_INTRUSION_OUTPUT_DIR / f"Store_{site_id}_FA_Intrusion.csv"
            fa_df.to_csv(fa_path, index=False)
            fa_intrusion_files += 1
            fa_intrusion_total_rows += len(fa_df)
        else:
            empty_fa += 1
    
    # Final report
    log.info("=" * 70)
    log.info("INDEXING COMPLETE")
    log.info("=" * 70)
    log.info("Total unique stores processed: %d", len(unique_sites))
    log.info("-" * 70)
    log.info("CCTV:")
    log.info("  Files created: %d", cctv_files)
    log.info("  Total rows: %d", cctv_total_rows)
    log.info("  Stores with no CCTV data: %d", empty_cctv)
    log.info("  Output: %s", CCTV_OUTPUT_DIR)
    log.info("-" * 70)
    log.info("FA/Intrusion:")
    log.info("  Files created: %d", fa_intrusion_files)
    log.info("  Total rows: %d", fa_intrusion_total_rows)
    log.info("  Stores with no FA/Intrusion data: %d", empty_fa)
    log.info("  Output: %s", FA_INTRUSION_OUTPUT_DIR)
    log.info("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
