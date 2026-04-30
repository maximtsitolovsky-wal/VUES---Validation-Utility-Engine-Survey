import csv
from pathlib import Path

# Check a sample FA/Intrusion file
fa_dir = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\FA&Intrusion STORES DATA - Survey')
files = list(fa_dir.glob('*.csv'))

print(f"Checking first file: {files[0].name}", flush=True)
print("=" * 70, flush=True)

with open(files[0], 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    
    print("Key columns:", flush=True)
    print(f"  E (4): {header[4]}", flush=True)
    print(f"  F (5): {header[5]}", flush=True)
    print(f"  I (8): {header[8]}", flush=True)
    print(f"  BB (53): {header[53]}", flush=True)
    print(flush=True)
    
    # Show first 5 data rows
    print("Sample rows (E, F, I, BB):", flush=True)
    for i, row in enumerate(reader):
        if i >= 10:
            break
        if len(row) > 53:
            e_val = row[4] if row[4] else "(empty)"
            f_val = row[5][:30] if row[5] else "(empty)"
            i_val = row[8] if row[8] else "(empty)"
            bb_val = row[53] if row[53] else "(empty)"
            print(f"  {e_val:10} | {f_val:30} | {i_val:10} | {bb_val}", flush=True)

# Count device types across all files
print(flush=True)
print("=" * 70, flush=True)
print("Sampling device types from multiple files...", flush=True)

type_counts = {}
coord_counts = {}
sample_count = 0

for f in files[:100]:  # Sample first 100 files
    with open(f, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # skip header
        for row in reader:
            if len(row) > 53 and row[8]:
                dtype = row[8]
                type_counts[dtype] = type_counts.get(dtype, 0) + 1
                coord = row[53] if len(row) > 53 else ""
                if coord:
                    coord_counts[coord] = coord_counts.get(coord, 0) + 1
                sample_count += 1

print(f"\nDevice types found (from {sample_count} rows in 100 files):", flush=True)
for dtype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f"  {dtype}: {count}", flush=True)

print(f"\nCoordinates found:", flush=True)
for coord, count in sorted(coord_counts.items(), key=lambda x: -x[1]):
    print(f"  {coord}: {count}", flush=True)
