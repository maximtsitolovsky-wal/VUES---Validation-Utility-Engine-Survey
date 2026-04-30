import pandas as pd
from pathlib import Path

f = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\fasheet.xlsx')
print(f"File: {f.name}", flush=True)
print(f"Exists: {f.exists()}", flush=True)
print(f"Size: {f.stat().st_size / 1024:.1f} KB", flush=True)

xl = pd.ExcelFile(f, engine='calamine')
print(f"\nSheets: {xl.sheet_names}", flush=True)

for sheet in xl.sheet_names:
    print(f"\n=== Sheet: {sheet} ===", flush=True)
    df = pd.read_excel(xl, sheet_name=sheet, nrows=10)
    print(f"Columns: {list(df.columns)}", flush=True)
    print(f"Rows: {len(df)}", flush=True)
    print("\nFirst 5 rows:", flush=True)
    print(df.head().to_string(), flush=True)
