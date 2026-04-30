#!/usr/bin/env python
"""Data integrity audit - verify no rows were lost during indexing."""

import pandas as pd
from pathlib import Path

# Load source data
print('Loading source workbook...')
xl = pd.ExcelFile(
    r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Microsoft Teams Chat Files\Camera&Alarm Ref Data 1.xlsx', 
    engine='calamine'
)

total_source = 0
for sheet in xl.sheet_names:
    df = pd.read_excel(xl, sheet_name=sheet, dtype=str)
    print(f'  {sheet}: {len(df):,} rows')
    total_source += len(df)

print(f'\nSOURCE TOTAL: {total_source:,} rows')

# Count output files
cctv_dir = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CCTV STORES DATA - Survey')
fa_dir = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\FA&Intrusion STORES DATA - Survey')

print('\nCounting output rows (this may take a moment)...')

cctv_rows = 0
cctv_files = list(cctv_dir.glob('*.csv'))
for i, f in enumerate(cctv_files):
    if i % 1000 == 0 and i > 0:
        print(f'  CCTV: {i}/{len(cctv_files)} files processed...')
    cctv_rows += sum(1 for _ in open(f, 'r', encoding='utf-8')) - 1  # -1 for header

fa_rows = 0
fa_files = list(fa_dir.glob('*.csv'))
for i, f in enumerate(fa_files):
    if i % 1000 == 0 and i > 0:
        print(f'  FA: {i}/{len(fa_files)} files processed...')
    fa_rows += sum(1 for _ in open(f, 'r', encoding='utf-8')) - 1  # -1 for header

print(f'\nOUTPUT:')
print(f'  CCTV: {len(cctv_files):,} files, {cctv_rows:,} rows')
print(f'  FA/Intrusion: {len(fa_files):,} files, {fa_rows:,} rows')

output_total = cctv_rows + fa_rows
print(f'\nOUTPUT TOTAL: {output_total:,} rows')

print('\n' + '='*50)
if output_total == total_source:
    print('✅ PERFECT MATCH! No data lost.')
else:
    diff = total_source - output_total
    print(f'⚠️  DIFFERENCE: {diff:,} rows')
    print(f'   Source: {total_source:,}')
    print(f'   Output: {output_total:,}')
    if diff > 0:
        print(f'\n   Possible causes:')
        print(f'   - Rows with empty/invalid Site ID (skipped)')
        print(f'   - Duplicate rows in overlapping stores')
