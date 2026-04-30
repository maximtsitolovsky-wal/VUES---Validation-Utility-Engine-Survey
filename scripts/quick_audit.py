#!/usr/bin/env python
"""Quick audit - check for skipped rows."""
import sys
import pandas as pd

print('Loading workbook...', flush=True)
xl = pd.ExcelFile(
    r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Microsoft Teams Chat Files\Camera&Alarm Ref Data 1.xlsx', 
    engine='calamine'
)

empty_site_count = 0
total = 0

for sheet in xl.sheet_names:
    print(f'Checking {sheet}...', flush=True)
    df = pd.read_excel(xl, sheet_name=sheet, dtype=str)
    total += len(df)
    
    site_col = 'SelectedSiteID'
    empty_mask = df[site_col].isna() | (df[site_col].astype(str).str.strip() == '')
    empty_count = empty_mask.sum()
    empty_site_count += empty_count
    
    if empty_count > 0:
        print(f'  -> {empty_count:,} rows with empty Site ID', flush=True)

print(flush=True)
print('='*50, flush=True)
print(f'Total rows in source: {total:,}', flush=True)
print(f'Rows with empty Site ID (skipped): {empty_site_count:,}', flush=True)
print(f'Rows that should be indexed: {total - empty_site_count:,}', flush=True)
print(flush=True)

# From our script output:
indexed_cctv = 1113580
indexed_fa = 670135
indexed_total = indexed_cctv + indexed_fa
expected = total - empty_site_count

print(f'Indexed total (CCTV + FA): {indexed_total:,}', flush=True)
print(f'Expected (source - empty): {expected:,}', flush=True)
print(flush=True)

if indexed_total == expected:
    print('✅ ALL DATA ACCOUNTED FOR!', flush=True)
else:
    diff = expected - indexed_total
    print(f'⚠️  Difference: {diff:,} rows', flush=True)

sys.stdout.flush()
