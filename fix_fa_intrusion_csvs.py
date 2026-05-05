"""
Script to fix FA&Intrusion CSV files:
1. Change header from "Abbreviated Names" to "Abbreviated Name"
2. Update coordinates based on System Type:
   - Fire Alarm / Intrusion Detection → (10.00, 50.00)
   - Alarm (standalone) → (10.00, 20.00)
"""

import os
import csv
import re
from pathlib import Path

# Directory containing the CSV files
DATA_DIR = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\FA&Intrusion STORES DATA - Survey")

def update_coordinates(system_type: str, current_coords: str) -> str:
    """Update coordinates based on system type."""
    if not current_coords or not current_coords.strip():
        return current_coords
    
    system_type_lower = system_type.lower() if system_type else ""
    
    # Fire Alarm or Intrusion Detection → (10.00, 50.00)
    if "fire" in system_type_lower or "intrusion" in system_type_lower:
        return '(10.00, 50.00)'
    # Plain Alarm (not Fire Alarm) → (10.00, 20.00)
    elif "alarm" in system_type_lower:
        return '(10.00, 20.00)'
    
    # Return unchanged if no match
    return current_coords


def process_csv_file(filepath: Path) -> tuple[bool, str]:
    """
    Process a single CSV file.
    Returns (success, message).
    """
    try:
        # Read the file
        with open(filepath, 'r', encoding='utf-8-sig', newline='') as f:
            content = f.read()
        
        # Read as CSV
        with open(filepath, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        if not rows:
            return False, "Empty file"
        
        header = rows[0]
        
        # Find column indices
        try:
            abbrev_names_idx = header.index("Abbreviated Names")
        except ValueError:
            # Already renamed or doesn't exist
            abbrev_names_idx = None
            try:
                abbrev_names_idx = header.index("Abbreviated Name")
            except ValueError:
                pass
        
        try:
            system_type_idx = header.index("System Type")
        except ValueError:
            return False, "No 'System Type' column found"
        
        try:
            coords_idx = header.index("Coordinates")
        except ValueError:
            return False, "No 'Coordinates' column found"
        
        # Fix header: "Abbreviated Names" → "Abbreviated Name"
        header_changed = False
        if "Abbreviated Names" in header:
            idx = header.index("Abbreviated Names")
            header[idx] = "Abbreviated Name"
            rows[0] = header
            header_changed = True
        
        # Fix coordinates based on System Type
        coords_changed = 0
        for i, row in enumerate(rows[1:], start=1):
            if len(row) > max(system_type_idx, coords_idx):
                system_type = row[system_type_idx] if system_type_idx < len(row) else ""
                current_coords = row[coords_idx] if coords_idx < len(row) else ""
                
                new_coords = update_coordinates(system_type, current_coords)
                if new_coords != current_coords:
                    row[coords_idx] = new_coords
                    rows[i] = row
                    coords_changed += 1
        
        # Write back
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        
        return True, f"Header: {'changed' if header_changed else 'already correct'}, Coords updated: {coords_changed}"
    
    except Exception as e:
        return False, f"Error: {str(e)}"


def main():
    print(f"Processing CSV files in: {DATA_DIR}")
    print("-" * 60)
    
    csv_files = list(DATA_DIR.glob("*.csv"))
    print(f"Found {len(csv_files)} CSV files")
    print("-" * 60)
    
    success_count = 0
    error_count = 0
    
    for filepath in csv_files:
        success, message = process_csv_file(filepath)
        if success:
            success_count += 1
            print(f"[OK] {filepath.name}: {message}")
        else:
            error_count += 1
            print(f"[ERR] {filepath.name}: {message}")
    
    print("-" * 60)
    print(f"Done! Processed: {success_count} | Errors: {error_count}")


if __name__ == "__main__":
    main()
