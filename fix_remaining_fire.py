"""
Fill remaining undetermined System Type rows with Fire Alarm.
"""

import csv
from pathlib import Path

DATA_DIR = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\FA&Intrusion STORES DATA - Survey")

csv_files = list(DATA_DIR.glob("*.csv"))
print(f"Processing {len(csv_files)} files...")
print()

total_fixed = 0
files_modified = 0

for i, filepath in enumerate(csv_files, 1):
    try:
        rows = []
        modified = False
        
        with open(filepath, 'r', newline='', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader)
            rows.append(header)
            
            try:
                system_type_idx = header.index("System Type")
                device_task_type_idx = header.index("Device/Task Type")
            except ValueError:
                continue
            
            for row in reader:
                # Ensure row has enough columns
                while len(row) <= max(system_type_idx, device_task_type_idx):
                    row.append("")
                
                system_type = row[system_type_idx].strip()
                
                # If not already set to valid value, set to Fire Alarm
                if system_type not in ["Fire Alarm", "Intrusion Detection"]:
                    row[system_type_idx] = "Fire Alarm"
                    row[device_task_type_idx] = "General Fire"
                    modified = True
                    total_fixed += 1
                
                rows.append(row)
        
        if modified:
            files_modified += 1
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
        
        if i % 500 == 0 or i == len(csv_files):
            print(f"Progress: {i}/{len(csv_files)} files...")
                
    except Exception as e:
        print(f"Error processing {filepath.name}: {e}")

print()
print("=" * 50)
print("Done!")
print(f"  Files modified: {files_modified}")
print(f"  Rows fixed: {total_fixed}")
print("=" * 50)
