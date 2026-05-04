"""Diagnostic script for Survey Routing table in Airtable.

Investigates:
1. What fields exist in the table
2. Current records in the table
3. What the specific view contains

Base ID: appAwgaX89x0JxG3Z
Table ID: tbl4LbgPUluSrbG2K
View ID: viw4ZoQPQr42IHZSw
"""

import os
import json
import requests
from pathlib import Path
from typing import Any

# Constants
AIRTABLE_API_BASE = "https://api.airtable.com/v0"
BASE_ID = "appAwgaX89x0JxG3Z"
TABLE_ID = "tbl4LbgPUluSrbG2K"
VIEW_ID = "viw4ZoQPQr42IHZSw"


def load_token() -> str:
    """Load Airtable token from user config or environment."""
    # Try loading from ~/.siteowlqa/config.json
    config_path = Path.home() / ".siteowlqa" / "config.json"
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                token = config.get("airtable_token") or config.get("scout_airtable_token")
                if token:
                    return token
        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
    
    # Try environment variable
    token = os.getenv("AIRTABLE_TOKEN")
    if token:
        return token
    
    raise RuntimeError(
        "No Airtable token found. Please set AIRTABLE_TOKEN environment variable "
        "or ensure ~/.siteowlqa/config.json exists with valid credentials."
    )


def fetch_records(
    token: str,
    base_id: str,
    table_id: str,
    view_id: str = "",
    max_records: int = 100
) -> list[dict[str, Any]]:
    """Fetch records from Airtable table."""
    url = f"{AIRTABLE_API_BASE}/{base_id}/{table_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    params = {"pageSize": min(max_records, 100)}
    if view_id:
        params["view"] = view_id
    
    all_records = []
    
    print(f"\nFetching records from table {table_id}...")
    if view_id:
        print(f"Using view: {view_id}")
    
    while len(all_records) < max_records:
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            records = data.get("records", [])
            all_records.extend(records)
            
            print(f"  Fetched {len(records)} records (total: {len(all_records)})")
            
            offset = data.get("offset")
            if not offset:
                break
            params["offset"] = offset
            
        except requests.exceptions.HTTPError as e:
            print(f"Error fetching records: {e}")
            print(f"Response: {e.response.text}")
            raise
    
    return all_records


def analyze_fields(records: list[dict[str, Any]]) -> dict[str, set]:
    """Analyze all fields found in records."""
    field_analysis = {}
    
    for record in records:
        fields = record.get("fields", {})
        for field_name, field_value in fields.items():
            if field_name not in field_analysis:
                field_analysis[field_name] = {
                    "types": set(),
                    "sample_values": [],
                    "null_count": 0,
                    "total_count": 0
                }
            
            field_analysis[field_name]["total_count"] += 1
            
            if field_value is None or field_value == "":
                field_analysis[field_name]["null_count"] += 1
            else:
                value_type = type(field_value).__name__
                field_analysis[field_name]["types"].add(value_type)
                
                # Store sample values (up to 3)
                if len(field_analysis[field_name]["sample_values"]) < 3:
                    # Truncate long values
                    if isinstance(field_value, str) and len(field_value) > 50:
                        sample = field_value[:50] + "..."
                    elif isinstance(field_value, list):
                        sample = f"[{len(field_value)} items]"
                    else:
                        sample = field_value
                    field_analysis[field_name]["sample_values"].append(sample)
    
    return field_analysis


def print_field_analysis(field_analysis: dict):
    """Print field analysis in a readable format."""
    print("\n" + "="*80)
    print("FIELD ANALYSIS")
    print("="*80)
    
    if not field_analysis:
        print("No fields found in records!")
        return
    
    for field_name in sorted(field_analysis.keys()):
        info = field_analysis[field_name]
        print(f"\n[FIELD] {field_name}")
        print(f"   Type(s): {', '.join(info['types']) if info['types'] else 'N/A'}")
        print(f"   Records: {info['total_count']} total, {info['null_count']} empty")
        if info['sample_values']:
            print(f"   Samples: {info['sample_values']}")


def print_record_summary(records: list[dict[str, Any]]):
    """Print summary of records."""
    print("\n" + "="*80)
    print("RECORD SUMMARY")
    print("="*80)
    print(f"Total records: {len(records)}")
    
    if records:
        print(f"\nFirst record ID: {records[0].get('id')}")
        print(f"Last record ID: {records[-1].get('id')}")
        
        # Show sample of first record fields
        if records[0].get("fields"):
            print("\nFirst record fields:")
            for key, value in sorted(records[0]["fields"].items()):
                if isinstance(value, str) and len(value) > 100:
                    display_value = value[:100] + "..."
                elif isinstance(value, list):
                    display_value = f"[{len(value)} items]"
                else:
                    display_value = value
                print(f"  {key}: {display_value}")


def main():
    """Run diagnostics on Survey Routing table."""
    print("="*80)
    print("SURVEY ROUTING TABLE DIAGNOSTIC")
    print("="*80)
    print(f"Base ID: {BASE_ID}")
    print(f"Table ID: {TABLE_ID}")
    print(f"View ID: {VIEW_ID}")
    
    # Load token
    try:
        token = load_token()
        print("\n[OK] Airtable token loaded successfully")
    except Exception as e:
        print(f"\n[ERROR] Error loading token: {e}")
        return 1
    
    # Fetch all records (no view filter)
    print("\n" + "-"*80)
    print("PART 1: ALL RECORDS IN TABLE")
    print("-"*80)
    try:
        all_records = fetch_records(token, BASE_ID, TABLE_ID, view_id="", max_records=1000)
        print(f"\n[OK] Successfully fetched {len(all_records)} records")
        
        if all_records:
            field_analysis = analyze_fields(all_records)
            print_field_analysis(field_analysis)
            print_record_summary(all_records)
        else:
            print("\n[WARNING] No records found in table!")
    except Exception as e:
        print(f"\n[ERROR] Error fetching all records: {e}")
        return 1
    
    # Fetch records from specific view
    print("\n" + "-"*80)
    print(f"PART 2: RECORDS IN VIEW {VIEW_ID}")
    print("-"*80)
    try:
        view_records = fetch_records(token, BASE_ID, TABLE_ID, view_id=VIEW_ID, max_records=1000)
        print(f"\n[OK] Successfully fetched {len(view_records)} records from view")
        
        if view_records:
            print(f"\nView contains {len(view_records)} out of {len(all_records)} total records")
            print(f"View filters out: {len(all_records) - len(view_records)} records")
            
            # Show which records are in view vs not
            view_ids = {r["id"] for r in view_records}
            all_ids = {r["id"] for r in all_records}
            filtered_out = all_ids - view_ids
            
            if filtered_out:
                print(f"\nRecords NOT in view: {len(filtered_out)}")
                for rec_id in list(filtered_out)[:5]:
                    rec = next(r for r in all_records if r["id"] == rec_id)
                    fields = rec.get("fields", {})
                    print(f"  - {rec_id}: {fields}")
                if len(filtered_out) > 5:
                    print(f"  ... and {len(filtered_out) - 5} more")
        else:
            print("\n[WARNING] No records found in this view!")
            if all_records:
                print("   (But table has records - view filter may be excluding everything)")
    except Exception as e:
        print(f"\n[ERROR] Error fetching view records: {e}")
        return 1
    
    print("\n" + "="*80)
    print("DIAGNOSTIC COMPLETE")
    print("="*80)
    return 0


if __name__ == "__main__":
    exit(main())
