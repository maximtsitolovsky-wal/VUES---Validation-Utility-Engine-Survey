"""
Fix System Type (Column I) and Device/Task Type (Column J) in FA&Intrusion CSV files.

Rules:
- System Type must be "Fire Alarm" or "Intrusion Detection"  
- Device/Task Type must be "General Fire" or "General Intrusion Detection"
- These must match (Fire Alarm → General Fire, Intrusion Detection → General Intrusion Detection)
"""

import csv
import os
from pathlib import Path

# Directory containing the CSV files
DATA_DIR = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\FA&Intrusion STORES DATA - Survey")

# Mappings for existing System Type values to standardized values
SYSTEM_TYPE_MAPPING = {
    # Fire-related
    "FIRE": "Fire Alarm",
    "FTRBL": "Fire Alarm",      # Fire Trouble
    "FSUPV": "Fire Alarm",      # Fire Supervisory
    "Fire Alarm": "Fire Alarm",
    
    # Intrusion-related  
    "BURG": "Intrusion Detection",  # Burglary
    "RX": "Intrusion Detection",    # Pharmacy (security)
    "Intrusion Detection": "Intrusion Detection",
}

# Keywords to infer System Type from Description when System Type is empty
FIRE_KEYWORDS = [
    "FIRE", "SMOKE", "ANSUL", "FLOW", "PULL STATION", "TAMPER", "DRY SYS",
    "WATER FLOW", "SPRINKLER", "HEAT DET", "DUCT DET", "SUPPRESSION"
]

INTRUSION_KEYWORDS = [
    "BURG", "MOTION", "DOOR", "PANIC", "GUN CASE", "CLINIC", "RX", "TLE",
    "ACCESS", "ENTRY", "EXIT", "SECURITY", "ALARM"
]


def infer_system_type(row, system_type_idx, description_idx):
    """Infer the System Type from Description or other row data when System Type is empty."""
    current = row[system_type_idx].strip().upper() if system_type_idx < len(row) else ""
    
    # If we have a valid mapping, use it
    if current in SYSTEM_TYPE_MAPPING:
        return SYSTEM_TYPE_MAPPING[current]
    
    # Try to infer from Description column
    description = row[description_idx].strip().upper() if description_idx < len(row) else ""
    
    # Check for fire keywords first (more specific usually)
    for keyword in FIRE_KEYWORDS:
        if keyword in description:
            return "Fire Alarm"
    
    # Check for intrusion keywords
    for keyword in INTRUSION_KEYWORDS:
        if keyword in description:
            return "Intrusion Detection"
    
    # Also check the Name column (index 5) for hints
    name = row[5].strip().upper() if len(row) > 5 else ""
    for keyword in FIRE_KEYWORDS:
        if keyword in name:
            return "Fire Alarm"
    for keyword in INTRUSION_KEYWORDS:
        if keyword in name:
            return "Intrusion Detection"
    
    # Default - if we can't determine, leave as is but log it
    return None


def get_device_task_type(system_type):
    """Get the matching Device/Task Type for a given System Type."""
    if system_type == "Fire Alarm":
        return "General Fire"
    elif system_type == "Intrusion Detection":
        return "General Intrusion Detection"
    return ""


def process_csv_file(filepath):
    """Process a single CSV file and update columns I and J."""
    rows = []
    modified = False
    undetermined_count = 0
    
    with open(filepath, 'r', newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows.append(header)
        
        # Find column indices
        try:
            system_type_idx = header.index("System Type")
            device_task_type_idx = header.index("Device/Task Type")
        except ValueError:
            print(f"  ⚠️ Missing required columns, skipping: {filepath.name}")
            return False, 0
        
        # Find Description column for inference
        try:
            description_idx = header.index("Description")
        except ValueError:
            description_idx = 39  # Default position based on sample
        
        for row in reader:
            # Ensure row has enough columns
            while len(row) <= max(system_type_idx, device_task_type_idx):
                row.append("")
            
            original_system_type = row[system_type_idx]
            original_device_type = row[device_task_type_idx]
            
            # Determine the correct System Type
            new_system_type = infer_system_type(row, system_type_idx, description_idx)
            
            if new_system_type:
                row[system_type_idx] = new_system_type
                row[device_task_type_idx] = get_device_task_type(new_system_type)
                
                if row[system_type_idx] != original_system_type or row[device_task_type_idx] != original_device_type:
                    modified = True
            else:
                undetermined_count += 1
            
            rows.append(row)
    
    # Write back if modified
    if modified:
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
    
    return modified, undetermined_count


def main():
    print("🐕 FA&Intrusion Data Fix - System Type & Device/Task Type")
    print("=" * 60)
    print(f"Directory: {DATA_DIR}")
    print()
    
    csv_files = list(DATA_DIR.glob("*.csv"))
    print(f"Found {len(csv_files)} CSV files to process")
    print()
    
    modified_count = 0
    error_count = 0
    total_undetermined = 0
    
    for i, filepath in enumerate(csv_files, 1):
        try:
            modified, undetermined = process_csv_file(filepath)
            if modified:
                modified_count += 1
                status = "✅ Modified"
            else:
                status = "⏭️ No changes"
            
            total_undetermined += undetermined
            
            # Progress update every 100 files
            if i % 100 == 0 or i == len(csv_files):
                print(f"Progress: {i}/{len(csv_files)} files processed...")
                
        except Exception as e:
            error_count += 1
            print(f"  ❌ Error processing {filepath.name}: {e}")
    
    print()
    print("=" * 60)
    print("Summary:")
    print(f"  📁 Total files processed: {len(csv_files)}")
    print(f"  ✅ Files modified: {modified_count}")
    print(f"  ⏭️ Files unchanged: {len(csv_files) - modified_count - error_count}")
    print(f"  ❌ Errors: {error_count}")
    print(f"  ⚠️ Rows with undetermined System Type: {total_undetermined}")
    print()
    print("🐕 Done! Woof!")


if __name__ == "__main__":
    main()
