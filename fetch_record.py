"""Fetch a specific Airtable record by ID and display all its fields."""

import sys
import json
from pathlib import Path

# Add src to path so we can import siteowlqa modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from siteowlqa.config import load_config
from siteowlqa.airtable_client import AirtableClient

def display_record(record_id: str):
    """Fetch and display all fields for a specific Airtable record."""
    
    # Load configuration (includes Airtable credentials)
    print(f"Loading configuration...")
    try:
        cfg = load_config()
    except Exception as e:
        print(f"ERROR: Failed to load configuration: {e}")
        print("\nMake sure you have run: python -m siteowlqa.setup_config")
        print("Or ensure ~/.siteowlqa/config.json exists with valid Airtable credentials.")
        return
    
    # Create Airtable client
    print(f"Connecting to Airtable...")
    client = AirtableClient(cfg)
    
    # Fetch the record
    print(f"\nFetching record: {record_id}")
    try:
        fields = client.get_record_fields(record_id)
    except Exception as e:
        print(f"ERROR: Failed to fetch record: {e}")
        return
    
    # Display all fields
    print(f"\n{'='*80}")
    print(f"RECORD: {record_id}")
    print(f"{'='*80}\n")
    
    # Highlight key fields first
    key_fields = [
        "True Score",
        "Processing Status", 
        "Status",
        "Site Number",
        "Vendor Name",
        "Surveyor Email",
        "Score",
        "Submission ID",
        "Date of Survey",
        "Survey Type",
        "Archived File Path",
        "Archive Path",
        "File Path",
    ]
    
    print("KEY FIELDS:")
    print("-" * 80)
    for field in key_fields:
        if field in fields:
            value = fields[field]
            print(f"  {field:30s}: {value}")
    
    # Display all other fields
    print(f"\n{'ALL FIELDS:':}")
    print("-" * 80)
    for field_name in sorted(fields.keys()):
        value = fields[field_name]
        # Handle different types appropriately
        if isinstance(value, list):
            # Handle attachment arrays - show each attachment detail
            print(f"  {field_name:30s}:")
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    print(f"    [{i}]: {json.dumps(item, indent=6)}")
                else:
                    print(f"    [{i}]: {item}")
        elif isinstance(value, dict):
            print(f"  {field_name:30s}: {json.dumps(value, indent=4)}")
        elif isinstance(value, str) and len(value) > 500:
            # Only truncate very long strings
            display_value = value[:500] + "..."
            print(f"  {field_name:30s}: {display_value}")
        else:
            print(f"  {field_name:30s}: {value}")
    
    print(f"\n{'='*80}")
    print(f"Total fields: {len(fields)}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    record_id = "rec4N9ehkQmRjMxnP"
    display_record(record_id)
