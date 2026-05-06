"""Read CSV headers from the archived submission file."""

import csv
from pathlib import Path

def read_csv_headers(file_path):
    """Read and display CSV headers."""
    print(f"Reading CSV headers from archived file:")
    print(f"  {file_path}")
    print("=" * 80)
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            headers = next(reader)
            
            print(f"\nFound {len(headers)} columns in the submitted CSV file:\n")
            for i, header in enumerate(headers, 1):
                print(f"  {i:2d}. {header}")
            
            print("\n" + "=" * 80)
            print(f"Total columns: {len(headers)}")
            print("=" * 80)
            
            return headers
    except Exception as e:
        print(f"ERROR reading CSV: {e}")
        return None

def main():
    # Path to the archived submission file
    file_path = Path(r"C:\VUES\archive\submissions\2026\05\06\recBBZ5oqgJUjXZ4U_SiteOwl-Projects-Devices-Walmart_Retail-20260506-104406.csv")
    
    if not file_path.exists():
        print(f"ERROR: File not found at {file_path}")
        return
    
    headers = read_csv_headers(file_path)
    
    # Show what was reported as missing from the validation
    print("\nFrom Airtable validation notes:")
    print("-" * 80)
    print("Missing critical cols: ['Description']")
    print("Reference rows: 311 | Submitted rows: 170")
    print("-" * 80)

if __name__ == "__main__":
    main()
