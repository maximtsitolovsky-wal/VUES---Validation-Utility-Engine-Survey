"""Check Scout table for recent records and search for a specific record in both tables.

This script:
1. Fetches the 5 most recent records from the Scout table
2. Searches for record rec4N9ehkQmRjMxnP in both Scout and Survey tables
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Any
import requests

# Add src to path so we can import siteowlqa modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from siteowlqa.config import load_config
from siteowlqa.user_config import load_user_config

AIRTABLE_API_BASE = "https://api.airtable.com/v0"
TARGET_RECORD_ID = "rec4N9ehkQmRjMxnP"


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
    
    return datetime.min


def fetch_all_records(token: str, base_id: str, table_name: str) -> list[dict[str, Any]]:
    """Fetch all records from an Airtable table."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{AIRTABLE_API_BASE}/{base_id}/{table_name}"
    all_records = []
    offset = None
    
    while True:
        params = {}
        if offset:
            params["offset"] = offset
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            records = data.get("records", [])
            all_records.extend(records)
            
            offset = data.get("offset")
            if not offset:
                break
                
        except requests.exceptions.RequestException as e:
            print(f"❌ ERROR fetching records: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"   Response: {e.response.text}")
            return []
    
    return all_records


def find_record_by_id(token: str, base_id: str, table_name: str, record_id: str) -> dict[str, Any] | None:
    """Try to fetch a specific record by ID from a table."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{AIRTABLE_API_BASE}/{base_id}/{table_name}/{record_id}"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Could not fetch record {record_id} from {table_name}: {e}")
        return None


def display_record_summary(record: dict[str, Any], index: int = None):
    """Display a summary of a record."""
    fields = record.get("fields", {})
    record_id = record.get("id", "")
    created_time = record.get("createdTime", "")
    
    # Extract key fields (using common field names)
    submission_id = fields.get("Submission ID", "N/A")
    vendor_name = fields.get("Vendor Name", "N/A")
    vendor_email = fields.get("Surveyor Email", "N/A")
    site_number = fields.get("Site Number", "N/A")
    submitted_at = fields.get("Date of Survey", "N/A")
    status = fields.get("Processing Status", "N/A")
    score = fields.get("Score", "N/A")
    true_score = fields.get("True Score", "N/A")
    
    if index is not None:
        print(f"[{index}] {submission_id}")
    else:
        print(f"📄 {submission_id}")
    
    print(f"    Record ID:     {record_id}")
    print(f"    Site Number:   {site_number}")
    print(f"    Vendor:        {vendor_name}")
    print(f"    Email:         {vendor_email}")
    print(f"    Status:        {status}")
    print(f"    Score:         {score}")
    print(f"    True Score:    {true_score}")
    print(f"    Submitted At:  {submitted_at}")
    print(f"    Created Time:  {created_time}")
    print()


def display_full_record(record: dict[str, Any], table_name: str):
    """Display all fields of a record."""
    fields = record.get("fields", {})
    record_id = record.get("id", "")
    
    print("=" * 80)
    print(f"FOUND IN TABLE: {table_name}")
    print(f"RECORD ID: {record_id}")
    print("=" * 80)
    print()
    
    # Display all fields
    print("ALL FIELDS:")
    print("-" * 80)
    for field_name in sorted(fields.keys()):
        value = fields[field_name]
        if isinstance(value, (list, dict)):
            print(f"  {field_name:30s}: {str(value)[:100]}")
        else:
            print(f"  {field_name:30s}: {value}")
    
    print()
    print("=" * 80)
    print()


def main():
    """Main execution."""
    print("=" * 80)
    print("VUES AIRTABLE QUERY TOOL")
    print("=" * 80)
    print()
    
    # Load configuration
    try:
        user_cfg = load_user_config()
        app_cfg = load_config()
    except Exception as e:
        print(f"❌ ERROR: Failed to load configuration: {e}")
        print("\nMake sure you have run: python -m siteowlqa.setup_config")
        print("Or ensure ~/.siteowlqa/config.json exists with valid Airtable credentials.")
        return 1
    
    # Extract Survey table config
    survey_token = user_cfg.airtable_token
    survey_base_id = user_cfg.airtable_base_id
    survey_table_name = user_cfg.airtable_table_name
    
    # Extract Scout table config
    scout_token = user_cfg.scout_airtable_token or user_cfg.airtable_token
    scout_base_id = user_cfg.scout_airtable_base_id
    scout_table_name = user_cfg.scout_airtable_table_name
    
    print(f"Survey Table: {survey_base_id} / {survey_table_name}")
    print(f"Scout Table:  {scout_base_id} / {scout_table_name}")
    print()
    
    # Check if Scout is configured
    if not scout_base_id or not scout_table_name:
        print("⚠️  WARNING: Scout table not configured!")
        print("   Scout base_id or table_name is missing from user config.")
        print()
    
    # ========================================================================
    # TASK 1: Fetch 5 most recent records from Scout table
    # ========================================================================
    
    if scout_base_id and scout_table_name:
        print("=" * 80)
        print("TASK 1: Fetching 5 most recent records from Scout table")
        print("=" * 80)
        print()
        
        print(f"Fetching all records from Scout table...")
        scout_records = fetch_all_records(scout_token, scout_base_id, scout_table_name)
        print(f"Retrieved {len(scout_records)} total records")
        print()
        
        if scout_records:
            # Sort by date
            def get_sort_date(record: dict[str, Any]) -> datetime:
                fields = record.get("fields", {})
                
                # Try submitted_at field
                submitted_at = fields.get("Date of Survey", "")
                if submitted_at:
                    dt = parse_date(str(submitted_at))
                    if dt != datetime.min:
                        return dt
                
                # Fall back to createdTime
                created_time = record.get("createdTime", "")
                return parse_date(str(created_time))
            
            sorted_records = sorted(scout_records, key=get_sort_date, reverse=True)
            
            print("=" * 80)
            print("5 MOST RECENT SCOUT RECORDS")
            print("=" * 80)
            print()
            
            for i, record in enumerate(sorted_records[:5], 1):
                display_record_summary(record, i)
            
            print("=" * 80)
            print()
        else:
            print("⚠️  No records found in Scout table.")
            print()
    
    # ========================================================================
    # TASK 2: Search for specific record in both tables
    # ========================================================================
    
    print("=" * 80)
    print(f"TASK 2: Searching for record {TARGET_RECORD_ID}")
    print("=" * 80)
    print()
    
    found_in_survey = False
    found_in_scout = False
    
    # Search in Survey table
    print(f"🔍 Searching in Survey table...")
    survey_record = find_record_by_id(survey_token, survey_base_id, survey_table_name, TARGET_RECORD_ID)
    if survey_record:
        found_in_survey = True
        print(f"✅ FOUND in Survey table!")
        print()
        display_full_record(survey_record, "Survey")
    else:
        print(f"❌ NOT FOUND in Survey table")
        print()
    
    # Search in Scout table (if configured)
    if scout_base_id and scout_table_name:
        print(f"🔍 Searching in Scout table...")
        scout_record = find_record_by_id(scout_token, scout_base_id, scout_table_name, TARGET_RECORD_ID)
        if scout_record:
            found_in_scout = True
            print(f"✅ FOUND in Scout table!")
            print()
            display_full_record(scout_record, "Scout")
        else:
            print(f"❌ NOT FOUND in Scout table")
            print()
    
    # Summary
    print("=" * 80)
    print("SEARCH SUMMARY")
    print("=" * 80)
    print(f"Record ID:        {TARGET_RECORD_ID}")
    print(f"Found in Survey:  {'✅ YES' if found_in_survey else '❌ NO'}")
    print(f"Found in Scout:   {'✅ YES' if found_in_scout else '❌ NO'}")
    
    if found_in_survey or found_in_scout:
        print()
        print("This was the Wachter site 5027 submission that scored 100.")
    
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
