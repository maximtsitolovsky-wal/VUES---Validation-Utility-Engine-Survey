"""Quick check of Scout and Survey Routing tables.

Queries:
1. Scout table (tblC4o9AvVulyxFMk) - Count records
2. Survey Routing table (tbl4LbgPUluSrbG2K) - List fields and check status
"""

import os
import json
import requests
from pathlib import Path
from typing import Any
from collections import Counter

# Constants
AIRTABLE_API_BASE = "https://api.airtable.com/v0"
BASE_ID = "appAwgaX89x0JxG3Z"
SCOUT_TABLE_ID = "tblC4o9AvVulyxFMk"
SURVEY_ROUTING_TABLE_ID = "tbl4LbgPUluSrbG2K"


def load_token() -> str:
    """Load Airtable token from user config or environment."""
    # Try loading from ~/.siteowlqa/config.json
    config_path = Path.home() / ".siteowlqa" / "config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                # For Scout base, use scout_airtable_token
                token = config.get("scout_airtable_token")
                if token:
                    print(f"[OK] Using scout_airtable_token from {config_path}")
                    return token
        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
    
    # Try environment variable
    token = os.getenv("AIRTABLE_TOKEN")
    if token:
        print("[OK] Using AIRTABLE_TOKEN from environment")
        return token
    
    raise RuntimeError(
        "No Airtable token found. Please set AIRTABLE_TOKEN environment variable "
        "or ensure ~/.siteowlqa/config.json exists with valid credentials."
    )


def fetch_all_records(
    token: str,
    base_id: str,
    table_id: str,
    max_records: int = 10000
) -> list[dict[str, Any]]:
    """Fetch all records from Airtable table with pagination."""
    url = f"{AIRTABLE_API_BASE}/{base_id}/{table_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    params = {"pageSize": 100}
    all_records = []
    
    while len(all_records) < max_records:
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            records = data.get("records", [])
            all_records.extend(records)
            
            offset = data.get("offset")
            if not offset:
                break
            params["offset"] = offset
            
        except requests.exceptions.HTTPError as e:
            print(f"Error fetching records: {e}")
            print(f"Response: {e.response.text}")
            raise
    
    return all_records


def check_scout_table(token: str):
    """Check Scout table and count records."""
    print("\n" + "="*80)
    print("SCOUT TABLE - tblC4o9AvVulyxFMk")
    print("="*80)
    
    try:
        records = fetch_all_records(token, BASE_ID, SCOUT_TABLE_ID)
        print(f"\n[OK] Total records in Scout table: {len(records)}")
        
        # Show some basic stats if records exist
        if records:
            print(f"\n  First record ID: {records[0].get('id')}")
            print(f"  Last record ID: {records[-1].get('id')}")
            
            # Count fields
            all_fields = set()
            for record in records:
                all_fields.update(record.get("fields", {}).keys())
            print(f"  Total unique fields: {len(all_fields)}")
            print(f"  Fields: {', '.join(sorted(all_fields))}")
        else:
            print("\n  [WARNING] No records found in Scout table!")
            
    except Exception as e:
        print(f"\n[ERROR] Error accessing Scout table: {e}")


def check_survey_routing_table(token: str):
    """Check Survey Routing table - list fields and analyze statuses."""
    print("\n" + "="*80)
    print("SURVEY ROUTING TABLE - tbl4LbgPUluSrbG2K")
    print("="*80)
    
    try:
        records = fetch_all_records(token, BASE_ID, SURVEY_ROUTING_TABLE_ID)
        print(f"\n[OK] Total records in Survey Routing table: {len(records)}")
        
        if not records:
            print("\n  [WARNING] No records found in Survey Routing table!")
            return
        
        # Collect all fields
        all_fields = set()
        field_stats = {}
        
        for record in records:
            fields = record.get("fields", {})
            for field_name, field_value in fields.items():
                all_fields.add(field_name)
                
                if field_name not in field_stats:
                    field_stats[field_name] = {
                        "populated": 0,
                        "empty": 0,
                        "sample_values": []
                    }
                
                if field_value is not None and field_value != "":
                    field_stats[field_name]["populated"] += 1
                    # Store sample values
                    if len(field_stats[field_name]["sample_values"]) < 3:
                        if isinstance(field_value, str):
                            sample = field_value[:50] + "..." if len(field_value) > 50 else field_value
                        elif isinstance(field_value, list):
                            sample = f"[{len(field_value)} items]"
                        else:
                            sample = str(field_value)
                        field_stats[field_name]["sample_values"].append(sample)
                else:
                    field_stats[field_name]["empty"] += 1
        
        # Display fields
        print(f"\nFIELDS IN SURVEY ROUTING TABLE ({len(all_fields)} total):")
        print("-" * 80)
        for field_name in sorted(all_fields):
            stats = field_stats[field_name]
            populated = stats["populated"]
            empty = stats["empty"]
            total = populated + empty
            percentage = (populated / total * 100) if total > 0 else 0
            
            print(f"\n  • {field_name}")
            print(f"    Populated: {populated}/{total} ({percentage:.1f}%)")
            if stats["sample_values"]:
                print(f"    Samples: {stats['sample_values']}")
        
        # Check for Status field specifically
        print("\n" + "="*80)
        print("STATUS ANALYSIS")
        print("="*80)
        
        status_field_names = [
            "Status", "status", "STATUS",
            "Processing Status", "Record Status"
        ]
        
        status_field = None
        for field_name in status_field_names:
            if field_name in all_fields:
                status_field = field_name
                break
        
        if status_field:
            print(f"\n[OK] Found status field: '{status_field}'")
            
            # Count status values
            status_values = []
            for record in records:
                status_val = record.get("fields", {}).get(status_field)
                if status_val:
                    status_values.append(status_val)
            
            status_counts = Counter(status_values)
            print(f"\nStatus breakdown:")
            for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {status}: {count}")
            
            # Show records without status
            no_status_count = len(records) - len(status_values)
            if no_status_count > 0:
                print(f"  (No status): {no_status_count}")
        else:
            print("\n[WARNING] No status field found. Available fields:")
            print(f"  {', '.join(sorted(all_fields))}")
            
            # Show sample record to help identify status
            print("\nSAMPLE RECORD (first record):")
            if records:
                sample = records[0].get("fields", {})
                for key, value in sorted(sample.items()):
                    if isinstance(value, str) and len(value) > 100:
                        display = value[:100] + "..."
                    elif isinstance(value, list):
                        display = f"[{len(value)} items]"
                    else:
                        display = value
                    print(f"  {key}: {display}")
        
    except Exception as e:
        print(f"\n[ERROR] Error accessing Survey Routing table: {e}")


def main():
    """Main function to check both tables."""
    print("="*80)
    print("AIRTABLE TABLES CHECK")
    print("="*80)
    print(f"Base ID: {BASE_ID}")
    print(f"Scout Table: {SCOUT_TABLE_ID}")
    print(f"Survey Routing Table: {SURVEY_ROUTING_TABLE_ID}")
    
    # Load token
    try:
        token = load_token()
    except Exception as e:
        print(f"\n[ERROR] Error loading token: {e}")
        return 1
    
    # Check Scout table
    check_scout_table(token)
    
    # Check Survey Routing table
    check_survey_routing_table(token)
    
    print("\n" + "="*80)
    print("CHECK COMPLETE")
    print("="*80)
    
    return 0


if __name__ == "__main__":
    exit(main())
