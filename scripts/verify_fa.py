import csv
from pathlib import Path

f = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\FA&Intrusion STORES DATA - Survey\Store_1000_FA_Intrusion.csv')
with open(f, 'r', encoding='utf-8') as file:
    reader = csv.reader(file)
    header = next(reader)
    row1 = next(reader)
    
print('Headers check:', flush=True)
print(f'  Abbreviated Names in headers: {"Abbreviated Names" in header}', flush=True)
print(f'  MAC Address in headers: {"MAC Address" in header}', flush=True)
print(flush=True)
print('Column BB (53):', header[53], '=', repr(row1[53]), flush=True)
print('Column BC (54):', header[54], '=', repr(row1[54]), flush=True)
