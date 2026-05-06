"""Download and check the CSV columns from the submitted file."""

import os
import sys
import json
import requests
import csv
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_airtable_token():
    """Get Airtable token from environment or config file."""
    # Try environment variable first
    token = os.getenv("AIRTABLE_TOKEN")
    if token:
        return token
    
    # Try config file
    config_path = Path.home() / ".siteowlqa" / "config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
                token = config.get("airtable_token")
                if token:
                    return token
        except Exception as e:
            print(f"Warning: Could not read config file: {e}")
    
    return None

def fetch_record(base_id: str, table_id: str, record_id: str, token: str):
    """Fetch a specific record from Airtable."""
    
    url = f"https://api.airtable.com/v0/{base_id}/{table_id}/{record_id}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ ERROR fetching record: {e}")
        sys.exit(1)

def download_csv(url: str, filename: str):
    """Download the CSV file from Airtable."""
    print(f"Downloading CSV file: {filename}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # Save to temp directory
        temp_path = Path("temp") / filename
        temp_path.parent.mkdir(exist_ok=True)
        
        with open(temp_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✓ Downloaded to: {temp_path}")
        return temp_path
    except Exception as e:
        print(f"❌ ERROR downloading file: {e}")
        sys.exit(1)

def read_csv_headers(file_path: Path):
    """Read and display CSV headers."""
    print(f"\nReading CSV headers from: {file_path.name}")
    print("=" * 80)
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            headers = next(reader)
            
            print(f"\n✓ Found {len(headers)} columns in the submitted CSV file:\n")
            for i, header in enumerate(headers, 1):
                print(f"  {i:2d}. {header}")
            
            print("\n" + "=" * 80)
            print(f"Total columns: {len(headers)}")
            print("=" * 80)
            
            return headers
    except Exception as e:
        print(f"❌ ERROR reading CSV: {e}")
        sys.exit(1)

def main():
    # Record details
    BASE_ID = "apptK6zNN0Hf3OuoJ"
    TABLE_ID = "tblo5JLmY0XhigcMO"
    RECORD_ID = "recBBZ5oqgJUjXZ4U"
    
    # Get Airtable token
    token = get_airtable_token()
    
    if not token:
        print("❌ ERROR: No Airtable token found!")
        sys.exit(1)
    
    # Fetch the record
    print(f"Fetching record {RECORD_ID}...")
    data = fetch_record(BASE_ID, TABLE_ID, RECORD_ID, token)
    
    # Get the uploaded file info
    fields = data.get("fields", {})
    upload_file = fields.get("Upload File", [])
    
    if not upload_file:
        print("❌ ERROR: No uploaded file found in this record")
        sys.exit(1)
    
    file_info = upload_file[0]
    file_url = file_info.get("url")
    file_name = file_info.get("filename")
    
    print(f"✓ Found uploaded file: {file_name}")
    
    # Download the CSV
    csv_path = download_csv(file_url, file_name)
    
    # Read and display headers
    headers = read_csv_headers(csv_path)
    
    # Also show what was expected to be missing from Notes
    notes = fields.get("Notes for Internal", "")
    print("\nFrom validation notes:")
    print("-" * 80)
    if "Missing critical cols:" in notes:
        missing_start = notes.find("Missing critical cols:")
        missing_end = notes.find("\n", missing_start)
        if missing_end == -1:
            missing_end = len(notes)
        print(notes[missing_start:missing_end])
    else:
        print("(No explicit missing columns info in notes)")
    print("-" * 80)

if __name__ == "__main__":
    main()
