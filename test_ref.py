#!/usr/bin/env python3
"""Quick test to check reference data for a site."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from siteowlqa.config import load_config
from siteowlqa.reference_data import fetch_reference_rows

cfg = load_config()
print(f"Reference source: {cfg.reference_source}")

site = "457"
print(f"Fetching reference for site {site}...")
df = fetch_reference_rows(cfg, site)
print(f"Total rows: {len(df)}")

if len(df) > 0:
    print(f"Columns: {list(df.columns)}")
    # Check FA/Intrusion rows
    has_abbrev = df['Abbreviated Name'].astype(str).str.strip().ne('') & (df['Abbreviated Name'].astype(str) != '0')
    has_desc = df['Description'].astype(str).str.strip().ne('') & (df['Description'].astype(str) != '0')
    fa_rows = len(df[has_abbrev | has_desc])
    cctv_rows = len(df[~(has_abbrev | has_desc)])
    print(f"FA/Intrusion rows: {fa_rows}")
    print(f"CCTV rows: {cctv_rows}")
    
    # Check FA breakdown
    only_abbrev = has_abbrev & ~has_desc
    only_desc = has_desc & ~has_abbrev
    both_cols = has_abbrev & has_desc
    print(f"FA rows with ONLY Abbreviated Name: {only_abbrev.sum()}")
    print(f"FA rows with ONLY Description: {only_desc.sum()}")
    print(f"FA rows with BOTH columns: {both_cols.sum()}")
