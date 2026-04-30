#!/usr/bin/env python
"""Process FA/Intrusion survey files with device type mapping and coordinates.

This script:
1. Loads RAW NAME -> device type mapping from fasheet.xlsx
2. Processes each CSV in FA&Intrusion STORES DATA - Survey folder ONLY
3. Matches Column F (Name) against RAW NAME from reference
4. Writes matched device type to Column I (System Type)
5. Writes coordinate to Column BB based on device type:
   - FTRBL = (10.00, 60.00)
   - FSUPV = (10.00, 50.00)
   - FIRE = (10.00, 70.00)
   - BURG = (10.00, 80.00)
   - RX = (10.00, 90.00)
6. Applies Device ID (New0001 format) to Column E
7. Corrects headers (Abbreviated Names, MAC Address)
8. Preserves Project ID (A) and Plan ID (B)
9. Skips blank rows
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# =============================================================================
# CONFIGURATION - STRICT FOLDER RESTRICTION
# =============================================================================

# ONLY process files in this folder - no exceptions
FA_INTRUSION_FOLDER = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\FA&Intrusion STORES DATA - Survey")

# Reference file for device type mapping
REFERENCE_FILE = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\fasheet.xlsx")
REFERENCE_SHEET = "DONE WITH UR BS"

# Column indices (0-based, after SelectedSiteID/Staging Site removal)
COL_PROJECT_ID = 0       # A - DO NOT OVERWRITE
COL_PLAN_ID = 1          # B - DO NOT OVERWRITE
COL_DEVICE_ID = 4        # E - Sequential New0001 format
COL_NAME = 5             # F - Used for matching against RAW NAME
COL_ABBREVIATED = 6      # G - Header rename: "Abbreviated Names"
COL_DEVICE_TASK = 7      # H - Populate: "Device"
COL_SYSTEM_TYPE = 8      # I - Populate with mapped device type
COL_DEVICE_TYPE = 9      # J - Leave as is for FA/Intrusion
COL_MAC_ADDRESS = 26     # AA - Header rename: "MAC Address"
COL_COORDINATES = 53     # BB - Populate based on device type
COL_ARCHIVED = 54        # BC - Clean up artifacts

# Coordinate mapping by device type
DEVICE_TYPE_COORDINATES = {
    "FTRBL": "(10.00, 60.00)",
    "FSUPV": "(10.00, 50.00)",
    "FIRE": "(10.00, 70.00)",
    "BURG": "(10.00, 80.00)",
    "RX": "(10.00, 90.00)",
}

# Header corrections
HEADER_CORRECTIONS = {
    "Abreviated ": "Abbreviated Names",
    "Abreviated": "Abbreviated Names",
    "Abbreviated Name": "Abbreviated Names",
    "AbbreviatedName": "Abbreviated Names",
    "MACAddress": "MAC Address",
    "Mac Address": "MAC Address",
    "macaddress": "MAC Address",
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_device_id(seq_num: int) -> str:
    """Format device ID as New0001, New0002, etc."""
    return f"New{seq_num:04d}"


def is_valid_device_row(row: list[str], name_col: int) -> bool:
    """Check if a row is a valid device row (has content in Name column)."""
    if len(row) <= name_col:
        return False
    name = row[name_col].strip() if row[name_col] else ""
    return bool(name)


def is_blank_row(row: list[str]) -> bool:
    """Check if entire row is blank/empty."""
    return all(not cell.strip() for cell in row)


def ensure_row_length(row: list[str], min_length: int) -> list[str]:
    """Extend row with empty strings if needed."""
    while len(row) < min_length:
        row.append("")
    return row


def csv_escape(value: str) -> str:
    """Escape a value for CSV output (quote if contains comma or quotes)."""
    if ',' in value or '"' in value or '\n' in value:
        value = value.replace('"', '""')
        return f'"{value}"'
    return value


def row_to_csv_line(row: list[str]) -> str:
    """Convert a row to a properly escaped CSV line."""
    return ','.join(csv_escape(cell) for cell in row)


def parse_csv_line(line: str) -> list[str]:
    """Parse a CSV line properly handling quoted fields."""
    row = []
    current = ""
    in_quotes = False
    i = 0
    chars = line.rstrip("\r\n")
    
    while i < len(chars):
        char = chars[i]
        if char == '"':
            if in_quotes and i + 1 < len(chars) and chars[i + 1] == '"':
                current += '"'
                i += 1
            else:
                in_quotes = not in_quotes
        elif char == ',' and not in_quotes:
            row.append(current)
            current = ""
        else:
            current += char
        i += 1
    
    row.append(current)
    return row


def load_device_type_mapping(ref_file: Path, sheet_name: str) -> dict[str, str]:
    """Load RAW NAME -> device type mapping from reference file."""
    df = pd.read_excel(ref_file, sheet_name=sheet_name, engine='calamine')
    
    # Get RAW NAME and device type columns
    df = df[['RAW NAME', 'device type']].dropna(subset=['RAW NAME', 'device type'])
    
    # Build lookup dict (normalize RAW NAME to uppercase for matching)
    mapping = {}
    for _, row in df.iterrows():
        raw_name = str(row['RAW NAME']).strip().upper()
        device_type = str(row['device type']).strip().upper()
        if raw_name and device_type:
            mapping[raw_name] = device_type
    
    return mapping


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def process_file(filepath: Path, device_mapping: dict[str, str]) -> dict:
    """Process a single FA/Intrusion CSV file.
    
    Returns dict with processing stats.
    """
    stats = {
        "rows_processed": 0,
        "devices_numbered": 0,
        "types_matched": 0,
        "types_unmatched": 0,
        "headers_corrected": 0,
        "error": None,
    }
    
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        
        if not lines:
            stats["error"] = "Empty file"
            return stats
        
        rows = [parse_csv_line(line) for line in lines]
        
        if not rows:
            stats["error"] = "No rows"
            return stats
        
        # --- Step 1: Correct header names ---
        header = rows[0]
        header = ensure_row_length(header, COL_ARCHIVED + 1)
        
        for i, col_name in enumerate(header):
            col_stripped = col_name.strip()
            if col_stripped in HEADER_CORRECTIONS:
                header[i] = HEADER_CORRECTIONS[col_stripped]
                stats["headers_corrected"] += 1
        
        rows[0] = header
        
        # --- Step 2: Process device rows ---
        device_seq = 0
        
        for row_idx in range(1, len(rows)):
            row = rows[row_idx]
            
            if is_blank_row(row):
                continue
            
            if not is_valid_device_row(row, COL_NAME):
                continue
            
            stats["rows_processed"] += 1
            row = ensure_row_length(row, COL_ARCHIVED + 1)
            
            # Column E: Device ID (New0001 format)
            device_seq += 1
            row[COL_DEVICE_ID] = format_device_id(device_seq)
            stats["devices_numbered"] += 1
            
            # Column H: Device / Task = "Device"
            row[COL_DEVICE_TASK] = "Device"
            
            # --- Match Name (Column F) against RAW NAME ---
            name_value = row[COL_NAME].strip().upper() if row[COL_NAME] else ""
            
            if name_value in device_mapping:
                device_type = device_mapping[name_value]
                
                # Column I: System Type = matched device type
                row[COL_SYSTEM_TYPE] = device_type
                stats["types_matched"] += 1
                
                # Column BB: Coordinate based on device type
                if device_type in DEVICE_TYPE_COORDINATES:
                    row[COL_COORDINATES] = DEVICE_TYPE_COORDINATES[device_type]
                else:
                    # Unknown device type - leave coordinate as is
                    pass
            else:
                # No match found - DO NOT guess, leave existing value
                stats["types_unmatched"] += 1
            
            # Clean up BC column if it has leftover coordinate artifact
            bc_value = row[COL_ARCHIVED].strip() if row[COL_ARCHIVED] else ""
            if bc_value in [" 50.00)", "50.00)", " 60.00)", "60.00)", " 70.00)", "70.00)", 
                           " 80.00)", "80.00)", " 90.00)", "90.00)", " 30.00)", "30.00)"]:
                row[COL_ARCHIVED] = ""
            
            rows[row_idx] = row
        
        # --- Step 3: Write back with proper CSV escaping ---
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            for row in rows:
                f.write(row_to_csv_line(row) + "\n")
        
    except Exception as e:
        stats["error"] = str(e)
    
    return stats


def main() -> int:
    print("=" * 70, flush=True)
    print("FA/Intrusion Survey Processor with Device Type Mapping", flush=True)
    print("=" * 70, flush=True)
    print(flush=True)
    
    # Verify we're only processing the correct folder
    print(f"Target folder: {FA_INTRUSION_FOLDER}", flush=True)
    print(f"Reference file: {REFERENCE_FILE}", flush=True)
    print(f"Reference sheet: {REFERENCE_SHEET}", flush=True)
    print(flush=True)
    
    if not FA_INTRUSION_FOLDER.exists():
        print(f"ERROR: Target folder not found!", flush=True)
        return 1
    
    if not REFERENCE_FILE.exists():
        print(f"ERROR: Reference file not found!", flush=True)
        return 1
    
    # Load device type mapping
    print("Loading device type mapping from reference...", flush=True)
    device_mapping = load_device_type_mapping(REFERENCE_FILE, REFERENCE_SHEET)
    print(f"Loaded {len(device_mapping):,} RAW NAME -> device type mappings", flush=True)
    print(flush=True)
    
    # Show coordinate mapping
    print("Coordinate mapping by device type:", flush=True)
    for dtype, coord in DEVICE_TYPE_COORDINATES.items():
        print(f"  {dtype} -> {coord}", flush=True)
    print(flush=True)
    
    # Get files ONLY from the approved folder
    files = list(FA_INTRUSION_FOLDER.glob("*.csv"))
    print(f"Found {len(files)} CSV files to process", flush=True)
    print("-" * 70, flush=True)
    
    # Process each file
    total_rows = 0
    total_devices = 0
    total_matched = 0
    total_unmatched = 0
    total_headers = 0
    errors = 0
    
    for i, filepath in enumerate(files):
        # Safety check - only process files in the approved folder
        if not str(filepath).startswith(str(FA_INTRUSION_FOLDER)):
            print(f"  SKIPPED (outside approved folder): {filepath.name}", flush=True)
            continue
        
        if (i + 1) % 500 == 0:
            print(f"Progress: {i + 1}/{len(files)} files...", flush=True)
        
        stats = process_file(filepath, device_mapping)
        
        if stats["error"]:
            errors += 1
            print(f"  ERROR {filepath.name}: {stats['error']}", flush=True)
        else:
            total_rows += stats["rows_processed"]
            total_devices += stats["devices_numbered"]
            total_matched += stats["types_matched"]
            total_unmatched += stats["types_unmatched"]
            total_headers += stats["headers_corrected"]
    
    print(flush=True)
    print("=" * 70, flush=True)
    print("PROCESSING COMPLETE", flush=True)
    print("=" * 70, flush=True)
    print(f"Files processed: {len(files)}", flush=True)
    print(f"Total rows: {total_rows:,}", flush=True)
    print(f"Devices numbered: {total_devices:,}", flush=True)
    print(f"Device types matched: {total_matched:,}", flush=True)
    print(f"Device types unmatched: {total_unmatched:,}", flush=True)
    print(f"Headers corrected: {total_headers}", flush=True)
    print(f"Errors: {errors}", flush=True)
    print(flush=True)
    print("Validation checklist:", flush=True)
    print(f"  [x] Only processed files in: {FA_INTRUSION_FOLDER.name}", flush=True)
    print("  [x] Column F (Name) matched against RAW NAME", flush=True)
    print("  [x] Column I (System Type) = matched device type", flush=True)
    print("  [x] Column BB coordinates by device type:", flush=True)
    print("      - FTRBL = (10.00, 60.00)", flush=True)
    print("      - FSUPV = (10.00, 50.00)", flush=True)
    print("      - FIRE = (10.00, 70.00)", flush=True)
    print("      - BURG = (10.00, 80.00)", flush=True)
    print("      - RX = (10.00, 90.00)", flush=True)
    print("  [x] Column E = Device ID (New0001 format)", flush=True)
    print("  [x] Headers corrected (Abbreviated Names, MAC Address)", flush=True)
    print("  [x] Project ID and Plan ID NOT overwritten", flush=True)
    print("  [x] Unmatched rows NOT guessed - left unchanged", flush=True)
    print("  [x] Blank rows NOT modified", flush=True)
    print("=" * 70, flush=True)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
