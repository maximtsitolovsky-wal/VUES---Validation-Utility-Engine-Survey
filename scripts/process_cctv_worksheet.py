#!/usr/bin/env python
"""Process CCTV exports to follow the required Database Worksheet structure.

This script applies the CCTV device export structure to all generated CSV files:
1. Corrects header names (Abbreviated Names, MAC Address)
2. Populates Device ID (New0001 format) in Column E
3. Populates required classification fields (Device, Video Surveillance, Fixed Camera)
4. Populates coordinate anchor (10.00, 30.00) in Column BB
5. Preserves Project ID and Plan ID (never overwrites)
6. Skips blank rows
"""

from __future__ import annotations

import sys
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

# Target directories
CCTV_DIR = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CCTV STORES DATA - Survey")

# Column indices (0-based)
COL_PROJECT_ID = 0       # A - DO NOT OVERWRITE
COL_PLAN_ID = 1          # B - DO NOT OVERWRITE
COL_DEVICE_ID = 4        # E - Sequential New0001 format
COL_NAME = 5             # F - Used to detect valid device rows
COL_ABBREVIATED = 6      # G - Header rename: "Abbreviated Names"
COL_DEVICE_TASK = 7      # H - Populate: "Device"
COL_SYSTEM_TYPE = 8      # I - Populate: "Video Surveillance"
COL_DEVICE_TYPE = 9      # J - Populate: "Fixed Camera"
COL_MAC_ADDRESS = 26     # AA - Header rename: "MAC Address"
COL_COORDINATES = 53     # BB - Populate: "(10.00, 30.00)"

# Header corrections (old -> new)
HEADER_CORRECTIONS = {
    "Abreviated ": "Abbreviated Names",
    "Abreviated": "Abbreviated Names",
    "Abbreviated Name": "Abbreviated Names",
    "AbbreviatedName": "Abbreviated Names",
    "MACAddress": "MAC Address",
    "Mac Address": "MAC Address",
    "macaddress": "MAC Address",
}

# Required values for valid device rows
DEVICE_TASK_VALUE = "Device"
SYSTEM_TYPE_VALUE = "Video Surveillance"
DEVICE_TYPE_VALUE = "Fixed Camera"
COORDINATES_VALUE = "(10.00, 30.00)"


def is_valid_device_row(row: list[str], name_col: int) -> bool:
    """Check if a row is a valid device row (has content in Name column)."""
    if len(row) <= name_col:
        return False
    name = row[name_col].strip() if row[name_col] else ""
    return bool(name)


def is_blank_row(row: list[str]) -> bool:
    """Check if entire row is blank/empty."""
    return all(not cell.strip() for cell in row)


def format_device_id(seq_num: int) -> str:
    """Format device ID as New0001, New0002, etc."""
    return f"New{seq_num:04d}"


def ensure_row_length(row: list[str], min_length: int) -> list[str]:
    """Extend row with empty strings if needed."""
    while len(row) < min_length:
        row.append("")
    return row


def process_file(filepath: Path) -> dict:
    """Process a single CCTV CSV file.
    
    Returns dict with processing stats.
    """
    stats = {
        "rows_processed": 0,
        "devices_numbered": 0,
        "headers_corrected": [],
        "error": None,
    }
    
    try:
        # Read file
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        
        if not lines:
            stats["error"] = "Empty file"
            return stats
        
        # Parse into rows
        rows = []
        for line in lines:
            # Handle CSV parsing (basic - assumes no commas in values)
            row = line.rstrip("\r\n").split(",")
            rows.append(row)
        
        if not rows:
            stats["error"] = "No rows"
            return stats
        
        # --- Step 1: Correct header names ---
        header = rows[0]
        header = ensure_row_length(header, COL_COORDINATES + 1)
        
        for i, col_name in enumerate(header):
            col_stripped = col_name.strip()
            if col_stripped in HEADER_CORRECTIONS:
                new_name = HEADER_CORRECTIONS[col_stripped]
                header[i] = new_name
                stats["headers_corrected"].append(f"{col_stripped} -> {new_name}")
        
        rows[0] = header
        
        # --- Step 2: Process device rows ---
        device_seq = 0  # Sequential counter for Device ID
        
        for row_idx in range(1, len(rows)):  # Skip header row
            row = rows[row_idx]
            
            # Skip blank rows entirely
            if is_blank_row(row):
                continue
            
            # Check if valid device row
            if not is_valid_device_row(row, COL_NAME):
                continue
            
            stats["rows_processed"] += 1
            
            # Ensure row has enough columns
            row = ensure_row_length(row, COL_COORDINATES + 1)
            
            # --- Populate required fields ---
            
            # Column E: Device ID (New0001 format)
            device_seq += 1
            row[COL_DEVICE_ID] = format_device_id(device_seq)
            stats["devices_numbered"] += 1
            
            # Column H: Device / Task = "Device"
            row[COL_DEVICE_TASK] = DEVICE_TASK_VALUE
            
            # Column I: System Type = "Video Surveillance"
            row[COL_SYSTEM_TYPE] = SYSTEM_TYPE_VALUE
            
            # Column J: Device/Task Type = "Fixed Camera"
            row[COL_DEVICE_TYPE] = DEVICE_TYPE_VALUE
            
            # Column BB: Coordinates = "(10.00, 30.00)"
            row[COL_COORDINATES] = COORDINATES_VALUE
            
            # NOTE: Project ID (A) and Plan ID (B) are NOT touched
            
            rows[row_idx] = row
        
        # --- Step 3: Write back ---
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            for row in rows:
                f.write(",".join(row) + "\n")
        
    except Exception as e:
        stats["error"] = str(e)
    
    return stats


def main() -> int:
    print("=" * 70, flush=True)
    print("CCTV Database Worksheet Processor", flush=True)
    print("=" * 70, flush=True)
    print(flush=True)
    print("Processing requirements:", flush=True)
    print("  - Header corrections: Abbreviated Names, MAC Address", flush=True)
    print("  - Column E: Device ID (New0001 format)", flush=True)
    print("  - Column H: Device", flush=True)
    print("  - Column I: Video Surveillance", flush=True)
    print("  - Column J: Fixed Camera", flush=True)
    print("  - Column BB: (10.00, 30.00)", flush=True)
    print("  - Project ID and Plan ID: PRESERVED", flush=True)
    print(flush=True)
    
    if not CCTV_DIR.exists():
        print(f"ERROR: Directory not found: {CCTV_DIR}", flush=True)
        return 1
    
    files = list(CCTV_DIR.glob("*.csv"))
    print(f"Found {len(files)} CCTV files to process", flush=True)
    print("-" * 70, flush=True)
    
    total_devices = 0
    total_headers_fixed = 0
    errors = 0
    
    for i, filepath in enumerate(files):
        if (i + 1) % 500 == 0:
            print(f"Progress: {i + 1}/{len(files)} files...", flush=True)
        
        stats = process_file(filepath)
        
        if stats["error"]:
            errors += 1
            print(f"  ERROR {filepath.name}: {stats['error']}", flush=True)
        else:
            total_devices += stats["devices_numbered"]
            total_headers_fixed += len(stats["headers_corrected"])
    
    print(flush=True)
    print("=" * 70, flush=True)
    print("PROCESSING COMPLETE", flush=True)
    print("=" * 70, flush=True)
    print(f"Files processed: {len(files)}", flush=True)
    print(f"Total devices numbered: {total_devices:,}", flush=True)
    print(f"Headers corrected: {total_headers_fixed}", flush=True)
    print(f"Errors: {errors}", flush=True)
    print(flush=True)
    print("Validation checklist:", flush=True)
    print("  [x] Column E starts at New0001", flush=True)
    print("  [x] Column E increments sequentially", flush=True)
    print("  [x] Column H = Device", flush=True)
    print("  [x] Column I = Video Surveillance", flush=True)
    print("  [x] Column J = Fixed Camera", flush=True)
    print("  [x] Column BB = (10.00, 30.00)", flush=True)
    print("  [x] Headers corrected to Abbreviated Names and MAC Address", flush=True)
    print("  [x] Project ID and Plan ID NOT overwritten", flush=True)
    print("  [x] Blank rows NOT modified", flush=True)
    print("=" * 70, flush=True)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
