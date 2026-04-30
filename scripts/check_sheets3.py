import pandas as pd
from pathlib import Path

# Check the big xlsm file
wb_path = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\DATA LAKE\Survey DL\SurveyData4.02.26.xlsm')
print(f'Checking: {wb_path.name}', flush=True)
print(f'Exists: {wb_path.exists()}', flush=True)
print(f'Size: {wb_path.stat().st_size / 1024 / 1024:.1f} MB', flush=True)

xl = pd.ExcelFile(wb_path, engine='calamine')
print('Sheets:', flush=True)
for s in xl.sheet_names:
    print(f'  - {s}', flush=True)
