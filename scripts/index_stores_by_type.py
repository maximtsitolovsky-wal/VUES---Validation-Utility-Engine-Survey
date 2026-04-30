#!/usr/bin/env python
"""Index stores by survey type - split the reference workbook into individual store CSVs.

OPTIMIZED VERSION - uses vectorized pandas operations for 1M+ row datasets.
NOW PROCESSES ALL SHEETS!

This script:
1. Loads ALL sheets from Camera&Alarm Ref Data workbook
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

# Paths
WORKBOOK_PATH = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Microsoft Teams Chat Files\Camera&Alarm Ref Data 1.xlsx")

CCTV_OUTPUT_DIR = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CCTV STORES DATA - Survey")
FA_INTRUSION_OUTPUT_DIR = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\FA&Intrusion STORES DATA - Survey")


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


def main() -> int:
    log.info("=" * 70)
    log.info("Store Indexing Script - OPTIMIZED for 1M+ rows")
    log.info("Processing ALL SHEETS")
    log.info("=" * 70)
    
    if not WORKBOOK_PATH.exists():
        log.error("Workbook not found: %s", WORKBOOK_PATH)
        return 1
    
    CCTV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FA_INTRUSION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get sheet names
    log.info("Loading workbook: %s", WORKBOOK_PATH.name)
    xl = pd.ExcelFile(WORKBOOK_PATH, engine="calamine")
    sheet_names = xl.sheet_names
    log.info("Found %d sheets: %s", len(sheet_names), sheet_names)
    
    # Load and combine all sheets
    all_dfs = []
    for sheet_name in sheet_names:
        log.info("Loading sheet: %s ...", sheet_name)
        df = pd.read_excel(xl, sheet_name=sheet_name, dtype=str)
        log.info("  -> %d rows, %d columns", len(df), len(df.columns))
        all_dfs.append(df)
    
    # Combine all sheets
    df = pd.concat(all_dfs, ignore_index=True)
    log.info("Combined total: %d rows", len(df))
    
    # Find required columns
    site_col = find_column(df, ["SelectedSiteID", "Selected Site ID", "SiteID", "Site ID", "Site Number"])
    if site_col is None:
        log.error("Could not find site ID column. Available: %s", list(df.columns)[:20])
        return 1
    log.info("Site ID column: %s", site_col)
    
    # Find split columns
    abbrev_col = find_column(df, ["Abreviated ", "Abreviated", "Abbreviated Name", "AbbreviatedName", "Abbreviated"])
    desc_col = find_column(df, ["Description"])
    
    if abbrev_col:
        log.info("Abbreviated column: '%s'", abbrev_col)
    else:
        log.warning("No Abbreviated column found")
        
    if desc_col:
        log.info("Description column: '%s'", desc_col)
    else:
        log.warning("No Description column found")
    
    # --- VECTORIZED SPLIT LOGIC ---
    log.info("Computing CCTV/FA split masks (vectorized)...")
    
    def col_has_content(col_name: str | None) -> pd.Series:
        if col_name is None or col_name not in df.columns:
            return pd.Series([False] * len(df), index=df.index)
        return df[col_name].fillna("").astype(str).str.strip().ne("")
    
    abbrev_has_content = col_has_content(abbrev_col)
    desc_has_content = col_has_content(desc_col)
    
    # CCTV = Abbreviated AND Description are EMPTY
    # FA/Intrusion = Abbreviated OR Description have CONTENT
    cctv_mask = ~abbrev_has_content & ~desc_has_content
    fa_mask = abbrev_has_content | desc_has_content
    
    log.info("Total CCTV rows: %d", cctv_mask.sum())
    log.info("Total FA/Intrusion rows: %d", fa_mask.sum())
    
    # Clean site IDs
    log.info("Normalizing site IDs...")
    df["__clean_site__"] = df[site_col].apply(clean_site_id)
    
    # Get unique sites
    unique_sites = df["__clean_site__"].loc[df["__clean_site__"].ne("")].unique()
    unique_sites = sorted(unique_sites)
    
    log.info("-" * 70)
    log.info("Found %d unique stores to process", len(unique_sites))
    log.info("-" * 70)
    
    # Pre-split dataframes
    cctv_df = df[cctv_mask].copy()
    fa_df = df[fa_mask].copy()
    
    # Group by site
    log.info("Grouping by site...")
    cctv_grouped = cctv_df.groupby("__clean_site__", sort=False)
    fa_grouped = fa_df.groupby("__clean_site__", sort=False)
    
    cctv_groups = {name: group.drop(columns=["__clean_site__"]) for name, group in cctv_grouped}
    fa_groups = {name: group.drop(columns=["__clean_site__"]) for name, group in fa_grouped}
    
    log.info("Writing individual store CSVs...")
    
    cctv_files = 0
    fa_files = 0
    cctv_total_rows = 0
    fa_total_rows = 0
    
    for i, site_id in enumerate(unique_sites, 1):
        if i % 500 == 0:
            log.info("Progress: %d / %d stores... (CCTV: %d, FA: %d)", 
                     i, len(unique_sites), cctv_files, fa_files)
        
        # Write CCTV file
        if site_id in cctv_groups:
            site_cctv = cctv_groups[site_id]
            if not site_cctv.empty:
                cctv_path = CCTV_OUTPUT_DIR / f"Store_{site_id}_CCTV.csv"
                site_cctv.to_csv(cctv_path, index=False)
                cctv_files += 1
                cctv_total_rows += len(site_cctv)
        
        # Write FA/Intrusion file
        if site_id in fa_groups:
            site_fa = fa_groups[site_id]
            if not site_fa.empty:
                fa_path = FA_INTRUSION_OUTPUT_DIR / f"Store_{site_id}_FA_Intrusion.csv"
                site_fa.to_csv(fa_path, index=False)
                fa_files += 1
                fa_total_rows += len(site_fa)
    
    # Final report
    log.info("=" * 70)
    log.info("INDEXING COMPLETE - ALL SHEETS PROCESSED")
    log.info("=" * 70)
    log.info("Sheets processed: %s", sheet_names)
    log.info("Total unique stores: %d", len(unique_sites))
    log.info("-" * 70)
    log.info("CCTV:")
    log.info("  Files created: %d", cctv_files)
    log.info("  Total rows: %d", cctv_total_rows)
    log.info("  Output: %s", CCTV_OUTPUT_DIR)
    log.info("-" * 70)
    log.info("FA/Intrusion:")
    log.info("  Files created: %d", fa_files)
    log.info("  Total rows: %d", fa_total_rows)
    log.info("  Output: %s", FA_INTRUSION_OUTPUT_DIR)
    log.info("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
