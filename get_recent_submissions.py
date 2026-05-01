"""Fetch the 5 most recent survey submissions from VUES Airtable.

This script retrieves submissions sorted by submitted_at or created_time descending
to verify that dashboard data is current.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Any

# Add src to path so we can import siteowlqa modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from siteowlqa.config import load_config, ATAIRTABLE_FIELDS as FIELDS
from siteowlqa.airtable_client import AirtableClient


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime for sorting."""
    if not date_str:
        return datetime.min
    
    # Try common date formats
    for fmt in [
        "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO format with milliseconds
        "%Y-%m-%dT%H:%M:%SZ",     # ISO format
        "%Y-%m-%d %H:%M:%S",      # Standard datetime
        "%Y-%m-%d",               # Date only
        "%m/%d/%Y",               # US format
        "%m/%d/%y",               # Short US format
    ]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # If all parsing fails, return min date
    return datetime.min


def main():
    """Fetch and display the 5 most recent survey submissions."""
    
    # Load app configuration (handles user config + .env)
    try:
        app_config = load_config()
    except EnvironmentError as e:
        print(f"❌ ERROR: {e}")
        return 1
    
    # Create Airtable client
    print(f"📡 Connecting to Airtable base: {app_config.airtable_base_id}")
    print(f"   Table: {app_config.airtable_table_name}")
    print()
    
    client = AirtableClient(app_config)
    
    # Fetch all raw records
    print("⏳ Fetching all records...")
    raw_records = client.list_all_raw_records()
    print(f"✅ Retrieved {len(raw_records)} total records")
    print()
    
    # Sort records by date (try submitted_at first, fall back to createdTime)
    def get_sort_date(record: dict[str, Any]) -> datetime:
        fields = record.get("fields", {})
        
        # Try submitted_at field (Date of Survey)
        submitted_at = fields.get(FIELDS.submitted_at, "")
        if submitted_at:
            dt = parse_date(str(submitted_at))
            if dt != datetime.min:
                return dt
        
        # Fall back to createdTime (Airtable system field)
        created_time = record.get("createdTime", "")
        return parse_date(str(created_time))
    
    sorted_records = sorted(raw_records, key=get_sort_date, reverse=True)
    
    # Display top 5
    print("=" * 80)
    print("📊 5 MOST RECENT SURVEY SUBMISSIONS")
    print("=" * 80)
    print()
    
    for i, record in enumerate(sorted_records[:5], 1):
        fields = record.get("fields", {})
        record_id = record.get("id", "")
        created_time = record.get("createdTime", "")
        
        # Extract key fields
        submission_id = fields.get(FIELDS.submission_id, "N/A")
        vendor_email = fields.get(FIELDS.vendor_email, "N/A")
        vendor_name = fields.get(FIELDS.vendor_name, "N/A")
        site_number = fields.get(FIELDS.site_number, "N/A")
        submitted_at = fields.get(FIELDS.submitted_at, "N/A")
        status = fields.get(FIELDS.status, "N/A")
        score = fields.get(FIELDS.score, "N/A")
        
        print(f"[{i}] {submission_id}")
        print(f"    Record ID:     {record_id}")
        print(f"    Site Number:   {site_number}")
        print(f"    Vendor:        {vendor_name}")
        print(f"    Email:         {vendor_email}")
        print(f"    Status:        {status}")
        print(f"    Score:         {score}")
        print(f"    Submitted At:  {submitted_at}")
        print(f"    Created Time:  {created_time}")
        print()
    
    print("=" * 80)
    print(f"✅ Done! Showing {min(5, len(sorted_records))} of {len(sorted_records)} total records")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
