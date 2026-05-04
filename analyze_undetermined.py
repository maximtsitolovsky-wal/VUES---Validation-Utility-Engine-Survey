"""
Analyze undetermined rows to find most common device names.
"""

import csv
from pathlib import Path
from collections import Counter

DATA_DIR = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\FA&Intrusion STORES DATA - Survey")

# Counters for analysis
name_counter = Counter()
description_counter = Counter()

csv_files = list(DATA_DIR.glob("*.csv"))
print(f"Scanning {len(csv_files)} files for undetermined rows...")

for filepath in csv_files:
    try:
        with open(filepath, 'r', newline='', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader)
            
            # Find column indices
            try:
                system_type_idx = header.index("System Type")
                name_idx = header.index("Name")
                description_idx = header.index("Description")
            except ValueError:
                continue
            
            for row in reader:
                if len(row) <= system_type_idx:
                    continue
                    
                # Check if System Type is empty or not one of the valid values
                system_type = row[system_type_idx].strip()
                if system_type not in ["Fire Alarm", "Intrusion Detection"]:
                    name = row[name_idx].strip() if len(row) > name_idx else ""
                    desc = row[description_idx].strip() if len(row) > description_idx else ""
                    
                    if name:
                        # Clean up the name - remove numbers at the end for grouping
                        import re
                        clean_name = re.sub(r'\s*\d+$', '', name).strip()
                        name_counter[clean_name] += 1
                    
                    if desc:
                        description_counter[desc] += 1
                        
    except Exception as e:
        pass

print()
print("=" * 70)
print("TOP 50 DEVICE NAMES (undetermined System Type)")
print("=" * 70)
print(f"{'Name':<50} {'Count':>10}")
print("-" * 70)
for name, count in name_counter.most_common(50):
    print(f"{name[:50]:<50} {count:>10}")

print()
print("=" * 70)
print("TOP 50 DESCRIPTIONS (undetermined System Type)")
print("=" * 70)
print(f"{'Description':<50} {'Count':>10}")
print("-" * 70)
for desc, count in description_counter.most_common(50):
    print(f"{desc[:50]:<50} {count:>10}")

print()
print(f"Total unique names: {len(name_counter)}")
print(f"Total unique descriptions: {len(description_counter)}")
