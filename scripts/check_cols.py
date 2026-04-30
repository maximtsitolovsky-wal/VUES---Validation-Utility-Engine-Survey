#!/usr/bin/env python
"""Remove columns A and BF from all exported CSVs."""
import sys
import pandas as pd
from pathlib import Path

# Check one file to see columns
cctv_dir = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CCTV STORES DATA - Survey')
f = list(cctv_dir.glob('*.csv'))[0]
df = pd.read_csv(f, nrows=1)
cols = list(df.columns)

print(f'Total columns: {len(cols)}', flush=True)
print(f'Column A (index 0): {cols[0]}', flush=True)
if len(cols) > 57:
    print(f'Column BF (index 57): {cols[57]}', flush=True)
else:
    print(f'Only {len(cols)} columns, no BF', flush=True)
