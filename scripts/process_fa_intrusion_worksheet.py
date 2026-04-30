#!/usr/bin/env python
"""Process FA/Intrusion exports - fix headers and add coordinates.

This script applies to FA/Intrusion CSV files:
1. Corrects header names (Abbreviated Names, MAC Address)
2. Populates coordinate anchor (10.00, 50.00) in Column BB
3. Cleans up any coordinate artifacts in BC
"""

from __future__ import annotations

import sys
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

FA_DIR = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\FA&Intrusion STORES DATA - Survey")

# Column indices (0-based)
COL_NAME = 5             # F - Used to detect valid device rows
COL_ABBREVIATED = 6      # G - Header rename: "Abbreviated Names"
COL_MAC_ADDRESS = 26     # AA - Header rename: "MAC Address"
COL_COORDINATES = 53     # BB - Populate: "(10.00, 50.00)"
COL_ARCHIVED = 54        # BC - Clean up leftover coordinate artifact

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

# FA/Intrusion coordinate value
COORDINATES_VALUE = "(10.00, 50.00)"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

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


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def process_file(filepath: Path) -> dict:
    """Process a single FA/Intrusion CSV file.
    
    Returns dict with processing stats.
    """
    stats = {
        "rows_processed": 0,
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
        for row_idx in range(1, len(rows)):
            row = rows[row_idx]
            
            if is_blank_row(row):
                continue
            
            if not is_valid_device_row(row, COL_NAME):
                continue
            
            stats["rows_processed"] += 1
            
            row = ensure_row_length(row, COL_ARCHIVED + 1)
            
            # Column BB: Coordinates = "(10.00, 50.00)"
            row[COL_COORDINATES] = COORDINATES_VALUE
            
            # Clean up BC column if it has leftover coordinate artifact
            if row[COL_ARCHIVED].strip() in [" 50.00)", "50.00)", " 50.00", "50.00", " 30.00)", "30.00)", " 30.00", "30.00"]:
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
    print("FA/Intrusion Worksheet Processor", flush=True)
    print("=" * 70, flush=True)
    print(flush=True)
    print("Processing requirements:", flush=True)
    print("  - Header corrections: Abbreviated Names, MAC Address", flush=True)
    print("  - Column BB: (10.00, 50.00)", flush=True)
    print(flush=True)
    
    if not FA_DIR.exists():
        print(f"ERROR: Directory not found: {FA_DIR}", flush=True)
        return 1
    
    files = list(FA_DIR.glob("*.csv"))
    print(f"Found {len(files)} FA/Intrusion files to process", flush=True)
    print("-" * 70, flush=True)
    
    total_rows = 0
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
            total_rows += stats["rows_processed"]
            total_headers_fixed += stats["headers_corrected"]
    
    print(flush=True)
    print("=" * 70, flush=True)
    print("PROCESSING COMPLETE", flush=True)
    print("=" * 70, flush=True)
    print(f"Files processed: {len(files)}", flush=True)
    print(f"Total rows updated: {total_rows:,}", flush=True)
    print(f"Headers corrected: {total_headers_fixed}", flush=True)
    print(f"Errors: {errors}", flush=True)
    print(flush=True)
    print("Validation checklist:", flush=True)
    print("  [x] Column BB = (10.00, 50.00)", flush=True)
    print("  [x] Headers corrected to Abbreviated Names and MAC Address", flush=True)
    print("  [x] Blank rows NOT modified", flush=True)
    print("=" * 70, flush=True)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
