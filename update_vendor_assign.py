import openpyxl
from pathlib import Path
from datetime import datetime

excel_path = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Documents\BaselinePrinter\Excel\Vendor ASSIGN. 4.2.26.xlsx')
print(f'Excel path: {excel_path}')
print(f'Exists: {excel_path.exists()}')

if not excel_path.exists():
    print('ERROR: Excel file not found!')
    exit(1)

wb = openpyxl.load_workbook(excel_path)
print(f'Sheets: {wb.sheetnames}')

# Check CEI sheet structure
if 'CEI' in wb.sheetnames:
    ws = wb['CEI']
    print(f'\nCEI sheet - first 3 rows:')
    for row in ws.iter_rows(min_row=1, max_row=3, max_col=5):
        print([cell.value for cell in row])
    print(f'CEI total rows: {ws.max_row}')

# Check if PTSI and alarmhawaii sheets exist
print(f'\nPTSI sheet exists: {"PTSI" in wb.sheetnames}')
print(f'alarmhawaii sheet exists: {"alarmhawaii" in wb.sheetnames or "alarmhawaii.com" in wb.sheetnames}')

wb.close()
