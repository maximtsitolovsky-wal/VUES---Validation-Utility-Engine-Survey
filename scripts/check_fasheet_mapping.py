import pandas as pd
from pathlib import Path

f = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\fasheet.xlsx')
df = pd.read_excel(f, sheet_name='DONE WITH UR BS', engine='calamine')

# Only keep RAW NAME and device type columns
df = df[['RAW NAME', 'device type']].dropna(subset=['RAW NAME'])
print(f'Total mappings: {len(df)}', flush=True)
print(f'\nUnique device types:', flush=True)
print(df['device type'].value_counts().to_string(), flush=True)
print(f'\nSample mappings:', flush=True)
print(df.head(20).to_string(), flush=True)
