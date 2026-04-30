#!/usr/bin/env python
"""Remove columns A (SelectedSiteID) and BF (Staging Site) from all exported CSVs."""
import sys
from pathlib import Path

# Directories
CCTV_DIR = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CCTV STORES DATA - Survey')
FA_DIR = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\FA&Intrusion STORES DATA - Survey')

# Columns to remove (by name for safety)
COLS_TO_REMOVE = {'SelectedSiteID', 'Staging Site'}

def process_file(filepath: Path) -> bool:
    """Remove specified columns from a CSV file. Returns True if modified."""
    try:
        # Read all lines
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        
        if not lines:
            return False
        
        # Parse header
        header = lines[0].rstrip('\r\n').split(',')
        
        # Find indices to remove
        indices_to_remove = set()
        for i, col in enumerate(header):
            if col.strip() in COLS_TO_REMOVE:
                indices_to_remove.add(i)
        
        if not indices_to_remove:
            return False  # Nothing to remove
        
        # Build new lines with columns removed
        new_lines = []
        for line in lines:
            parts = line.rstrip('\r\n').split(',')
            new_parts = [p for i, p in enumerate(parts) if i not in indices_to_remove]
            new_lines.append(','.join(new_parts) + '\n')
        
        # Write back
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            f.writelines(new_lines)
        
        return True
    except Exception as e:
        print(f'  ERROR {filepath.name}: {e}', flush=True)
        return False


def process_directory(dir_path: Path, label: str):
    """Process all CSVs in a directory."""
    files = list(dir_path.glob('*.csv'))
    print(f'\n{label}: {len(files)} files', flush=True)
    
    modified = 0
    for i, f in enumerate(files):
        if (i + 1) % 1000 == 0:
            print(f'  Progress: {i + 1}/{len(files)}...', flush=True)
        if process_file(f):
            modified += 1
    
    print(f'  Modified: {modified} files', flush=True)
    return modified


if __name__ == '__main__':
    print('='*60, flush=True)
    print('Removing columns: SelectedSiteID, Staging Site', flush=True)
    print('='*60, flush=True)
    
    total = 0
    total += process_directory(CCTV_DIR, 'CCTV')
    total += process_directory(FA_DIR, 'FA/Intrusion')
    
    print(flush=True)
    print('='*60, flush=True)
    print(f'DONE! Total files modified: {total}', flush=True)
    print('='*60, flush=True)
