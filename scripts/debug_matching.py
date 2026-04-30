import pandas as pd
from pathlib import Path

# Load mapping
ref = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\fasheet.xlsx')
df = pd.read_excel(ref, sheet_name='DONE WITH UR BS', engine='calamine')
df = df[['RAW NAME', 'device type']].dropna(subset=['RAW NAME', 'device type'])

# Build mapping dict
mapping = {}
for _, row in df.iterrows():
    raw_name = str(row['RAW NAME']).strip().upper()
    device_type = str(row['device type']).strip().upper()
    if raw_name and device_type:
        mapping[raw_name] = device_type

print(f"Total mappings: {len(mapping)}", flush=True)
print(flush=True)

# Check what names we're trying to match from Store_0
import csv
fa_file = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\FA&Intrusion STORES DATA - Survey\Store_0_FA_Intrusion.csv')

with open(fa_file, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    
    print("Checking matches for Store_0:", flush=True)
    print("-" * 60, flush=True)
    
    for i, row in enumerate(reader):
        if i >= 15:
            break
        if len(row) > 5:
            name = row[5].strip().upper() if row[5] else ""
            matched = name in mapping
            device_type = mapping.get(name, "NO MATCH")
            print(f"Name: '{name[:40]}'", flush=True)
            print(f"  -> Matched: {matched}, Type: {device_type}", flush=True)

print(flush=True)
print("=" * 60, flush=True)
print("Checking if similar names exist in mapping...", flush=True)

# Check for partial matches
test_names = ["HIRING CENTER MOTION", "HIRING CENTER", "HIRING CENTER MOTION 3"]
for name in test_names:
    key = name.upper()
    if key in mapping:
        print(f"'{name}' -> {mapping[key]}", flush=True)
    else:
        # Find similar
        similar = [k for k in list(mapping.keys())[:100] if "HIRING" in k]
        if similar:
            print(f"'{name}' NOT FOUND. Similar:", flush=True)
            for s in similar[:5]:
                print(f"  - '{s}' -> {mapping[s]}", flush=True)
