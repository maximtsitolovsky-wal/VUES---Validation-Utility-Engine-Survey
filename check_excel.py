import openpyxl
from pathlib import Path

excel_path = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Documents\BaselinePrinter\Excel\Vendor ASSIGN. 4.2.26.xlsx')
wb = openpyxl.load_workbook(excel_path, read_only=True)
ws = wb['CEI']

# Get headers
headers = [cell.value for cell in list(ws.iter_rows(min_row=1, max_row=1))[0]]
print('Headers:', headers)

# Get sample row
sample = [cell.value for cell in list(ws.iter_rows(min_row=2, max_row=2))[0]]
print('Sample:', sample)

wb.close()
