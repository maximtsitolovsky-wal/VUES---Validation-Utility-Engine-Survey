import pandas as pd
from pathlib import Path

# Check the latest workbook for sheet names
wb_path = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Microsoft Teams Chat Files\Camera&Alarm Ref Data 1.xlsx')
print(f"Checking: {wb_path}", flush=True)
print(f"Exists: {wb_path.exists()}", flush=True)

xl = pd.ExcelFile(wb_path, engine='calamine')
print('Sheets:', flush=True)
for s in xl.sheet_names:
    print(f'  - {s}', flush=True)
