import pandas as pd
from pathlib import Path

# Check the BaselinePrinter workbook
wb_path = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Documents\BaselinePrinter\Excel\Camera&Alarm Ref Data.xlsx')
print(f'Checking: {wb_path.name}', flush=True)
print(f'Exists: {wb_path.exists()}', flush=True)

xl = pd.ExcelFile(wb_path, engine='calamine')
print('Sheets:', flush=True)
for s in xl.sheet_names:
    print(f'  - {s}', flush=True)
