"""Fetch a specific Airtable record by ID and display all its fields."""

import sys
from pathlib import Path

# Add src to path so we can import siteowlqa modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from siteowlqa.config import AppConfig
from siteowlqa.airtable_client import AirtableClient

def display_record(record_id: str):
    """Fetch and display all fields for a specific Airtable record."""
    
    # Load configuration (includes Airtable credentials)
    print(f"Loading configuration...")
    try:
        cfg = AppConfig.from_env()
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
        # Truncate long values for readability
        if isinstance(value, str) and len(value) > 200:
            display_value = value[:200] + "..."
        elif isinstance(value, list) and len(value) > 0:
            # Handle attachment arrays
            display_value = f"[Array with {len(value)} items] - {value}"
        else:
            display_value = value
        print(f"  {field_name:30s}: {display_value}")
    
    print(f"\n{'='*80}")
    print(f"Total fields: {len(fields)}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    record_id = "rec4N9ehkQmRjMxnP"
    display_record(record_id)
