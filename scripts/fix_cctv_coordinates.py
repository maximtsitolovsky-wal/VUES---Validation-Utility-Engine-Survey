#!/usr/bin/env python
"""Fix CCTV exports - properly quote the coordinates value."""
import sys
from pathlib import Path

CCTV_DIR = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CCTV STORES DATA - Survey")

COL_DEVICE_ID = 4
COL_NAME = 5
COL_DEVICE_TASK = 7
COL_SYSTEM_TYPE = 8
COL_DEVICE_TYPE = 9
COL_COORDINATES = 53

DEVICE_TASK_VALUE = "Device"
SYSTEM_TYPE_VALUE = "Video Surveillance"
DEVICE_TYPE_VALUE = "Fixed Camera"
COORDINATES_VALUE = "(10.00, 30.00)"


def csv_escape(value: str) -> str:
    """Escape a value for CSV output."""
    if ',' in value or '"' in value or '\n' in value:
        value = value.replace('"', '""')
        return f'"{value}"'
    return value


def row_to_csv_line(row: list[str]) -> str:
    """Convert a row to a properly escaped CSV line."""
    return ','.join(csv_escape(cell) for cell in row)


def format_device_id(seq_num: int) -> str:
    return f"New{seq_num:04d}"


def is_valid_device_row(row: list[str], name_col: int) -> bool:
    if len(row) <= name_col:
        return False
    name = row[name_col].strip() if row[name_col] else ""
    return bool(name)


def is_blank_row(row: list[str]) -> bool:
    return all(not cell.strip() for cell in row)


def ensure_row_length(row: list[str], min_length: int) -> list[str]:
    while len(row) < min_length:
        row.append("")
    return row


def process_file(filepath: Path) -> int:
    """Process a single file. Returns device count."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        
        if not lines:
            return 0
        
        rows = []
        for line in lines:
            # Parse CSV properly (handle quoted fields)
            row = []
            current = ""
            in_quotes = False
            for char in line.rstrip("\r\n"):
                if char == '"':
                    in_quotes = not in_quotes
                elif char == ',' and not in_quotes:
                    row.append(current)
                    current = ""
                else:
                    current += char
            row.append(current)
            rows.append(row)
        
        device_seq = 0
        
        for row_idx in range(1, len(rows)):
            row = rows[row_idx]
            
            if is_blank_row(row):
                continue
            
            if not is_valid_device_row(row, COL_NAME):
                continue
            
            row = ensure_row_length(row, COL_COORDINATES + 1)
            
            device_seq += 1
            row[COL_DEVICE_ID] = format_device_id(device_seq)
            row[COL_DEVICE_TASK] = DEVICE_TASK_VALUE
            row[COL_SYSTEM_TYPE] = SYSTEM_TYPE_VALUE
            row[COL_DEVICE_TYPE] = DEVICE_TYPE_VALUE
            row[COL_COORDINATES] = COORDINATES_VALUE
            
            rows[row_idx] = row
        
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            for row in rows:
                f.write(row_to_csv_line(row) + "\n")
        
        return device_seq
    except Exception as e:
        print(f"  ERROR {filepath.name}: {e}", flush=True)
        return 0


def main() -> int:
    print("=" * 60, flush=True)
    print("Fixing CCTV coordinates (proper CSV quoting)", flush=True)
    print("=" * 60, flush=True)
    
    files = list(CCTV_DIR.glob("*.csv"))
    print(f"Found {len(files)} files", flush=True)
    
    total_devices = 0
    for i, f in enumerate(files):
        if (i + 1) % 500 == 0:
            print(f"Progress: {i + 1}/{len(files)}...", flush=True)
        total_devices += process_file(f)
    
    print(flush=True)
    print("=" * 60, flush=True)
    print(f"DONE! Devices processed: {total_devices:,}", flush=True)
    print("=" * 60, flush=True)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
