"""Fetch a specific Airtable record by ID from a specific base and table."""

import os
import sys
import json
import requests
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
    """Fetch a specific record from Airtable and display all fields."""
    
    url = f"https://api.airtable.com/v0/{base_id}/{table_id}/{record_id}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"Fetching record from Airtable...")
    print(f"  Base ID:   {base_id}")
    print(f"  Table ID:  {table_id}")
    print(f"  Record ID: {record_id}")
    print()
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract fields and metadata
        record_id_resp = data.get("id")
        created_time = data.get("createdTime")
        fields = data.get("fields", {})
        
        # Display the record
        print("=" * 80)
        print(f"RECORD DETAILS")
        print("=" * 80)
        print(f"Record ID:     {record_id_resp}")
        print(f"Created Time:  {created_time}")
        print()
        print("=" * 80)
        print("ALL FIELDS:")
        print("=" * 80)
        
        # Sort fields by name for easier reading
        for field_name in sorted(fields.keys()):
            value = fields[field_name]
            
            # Handle different types appropriately
            if isinstance(value, list):
                print(f"\n{field_name}:")
                if len(value) == 0:
                    print("  (empty list)")
                else:
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            print(f"  [{i}]:")
                            for k, v in item.items():
                                print(f"      {k}: {v}")
                        else:
                            print(f"  [{i}]: {item}")
            elif isinstance(value, dict):
                print(f"\n{field_name}:")
                for k, v in value.items():
                    print(f"  {k}: {v}")
            elif isinstance(value, str) and len(value) > 500:
                # Truncate very long strings
                print(f"{field_name}:")
                print(f"  {value[:500]}...")
                print(f"  (truncated - {len(value)} chars total)")
            else:
                print(f"{field_name}: {value}")
        
        print()
        print("=" * 80)
        print(f"Total fields: {len(fields)}")
        print("=" * 80)
        
        return data
        
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ ERROR: HTTP {e.response.status_code}")
        print(f"Response: {e.response.text}")
        if e.response.status_code == 401:
            print("\nAuthentication failed. Please check your Airtable token.")
        elif e.response.status_code == 404:
            print("\nRecord, table, or base not found. Please check the IDs.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)

def main():
    # Record details from user request
    BASE_ID = "apptK6zNN0Hf3OuoJ"
    TABLE_ID = "tblo5JLmY0XhigcMO"
    RECORD_ID = "recBBZ5oqgJUjXZ4U"
    
    # Get Airtable token
    token = get_airtable_token()
    
    if not token:
        print("❌ ERROR: No Airtable token found!")
        print()
        print("Please set your Airtable token in one of these ways:")
        print("  1. Set AIRTABLE_TOKEN environment variable in .env file")
        print("  2. Add 'airtable_token' to ~/.siteowlqa/config.json")
        print()
        sys.exit(1)
    
    # Fetch and display the record
    fetch_record(BASE_ID, TABLE_ID, RECORD_ID, token)

if __name__ == "__main__":
    main()
