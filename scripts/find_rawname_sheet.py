import pandas as pd
from pathlib import Path

files_to_check = [
    Path(r'C:\Users\vn59j7j\Documents\BaselinePrinter\SVG_IN\Camera&Alarm Ref Data.xlsx'),
    Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Documents\BaselinePrinter\Excel\Camera&Alarm Ref Data.xlsx'),
    Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Microsoft Teams Chat Files\Camera&Alarm Ref Data 1.xlsx'),
    Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Microsoft Teams Chat Files\Camera&Alarm Ref Data.xlsx'),
]

for f in files_to_check:
    if not f.exists():
        print(f"NOT FOUND: {f.name}", flush=True)
        continue
    
    print(f"\n=== {f.name} ===", flush=True)
    try:
        xl = pd.ExcelFile(f, engine='calamine')
        print(f"Sheets: {xl.sheet_names}", flush=True)
        
        # Check each sheet for RAW NAME column
        for sheet in xl.sheet_names:
            try:
                df = pd.read_excel(xl, sheet_name=sheet, nrows=5)
                cols = [str(c).strip().upper() for c in df.columns]
                if 'RAW NAME' in cols or 'RAWNAME' in cols or 'RAW_NAME' in cols:
                    print(f"  -> Sheet '{sheet}' has RAW NAME column!", flush=True)
                    print(f"     Columns: {list(df.columns)[:5]}", flush=True)
            except Exception as e:
                print(f"  -> Error reading sheet '{sheet}': {e}", flush=True)
    except Exception as e:
        print(f"  ERROR: {e}", flush=True)
