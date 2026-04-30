import csv
from pathlib import Path

f = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CCTV STORES DATA - Survey\Store_1000_CCTV.csv')
with open(f, 'r', encoding='utf-8') as file:
    reader = csv.reader(file)
    header = next(reader)
    row1 = next(reader)
    
print('Column BB (53):', header[53], '=', repr(row1[53]), flush=True)
print('Column BC (54):', header[54], '=', repr(row1[54]), flush=True)
print('Column BD (55):', header[55], '=', repr(row1[55]), flush=True)
