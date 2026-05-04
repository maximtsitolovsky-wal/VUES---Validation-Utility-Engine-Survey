"""Investigate the 'Awaiting Scout' status issue in Survey Routing table.

This script will:
1. Get all records from the table
2. Analyze all unique Status values
3. Count records for each status
4. Look for any records that should be 'Awaiting Scout'
"""

import os
import json
import requests
from pathlib import Path
from collections import Counter
from typing import Any

# Constants
AIRTABLE_API_BASE = "https://api.airtable.com/v0"
BASE_ID = "appAwgaX89x0JxG3Z"
TABLE_ID = "tbl4LbgPUluSrbG2K"


def load_token() -> str:
    """Load Airtable token from user config."""
    config_path = Path.home() / ".siteowlqa" / "config.json"
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                token = config.get("scout_airtable_token")
                if token:
                    return token
        except Exception as e:
            print(f"Error loading config: {e}")
    
    token = os.getenv("AIRTABLE_TOKEN")
    if token:
        return token
    
    raise RuntimeError("No Airtable token found")


def fetch_all_records(token: str, base_id: str, table_id: str) -> list[dict[str, Any]]:
    """Fetch ALL records from table."""
    url = f"{AIRTABLE_API_BASE}/{base_id}/{table_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    all_records = []
    params = {"pageSize": 100}
    
    print(f"Fetching all records from {table_id}...")
    
    while True:
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
    
    return all_records


def analyze_status_field(records: list[dict[str, Any]]):
    """Analyze the Status field in detail."""
    print("\n" + "="*80)
    print("STATUS FIELD ANALYSIS")
    print("="*80)
    
    # Count all status values
    status_counts = Counter()
    records_by_status = {}
    
    for record in records:
        fields = record.get("fields", {})
        status = fields.get("Status", "NO_STATUS")
        status_counts[status] += 1
        
        if status not in records_by_status:
            records_by_status[status] = []
        records_by_status[status].append(record)
    
    # Print status counts
    print(f"\nTotal records: {len(records)}")
    print(f"\nUnique status values: {len(status_counts)}")
    print("\nSTATUS VALUE COUNTS:")
    print("-" * 80)
    
    for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(records)) * 100
        print(f"  {status:30s} : {count:4d} ({percentage:5.1f}%)")
    
    # Check for "Awaiting Scout"
    print("\n" + "="*80)
    print("AWAITING SCOUT INVESTIGATION")
    print("="*80)
    
    awaiting_scout_variations = [
        "Awaiting Scout",
        "awaiting scout",
        "Awaiting scout",
        "AWAITING SCOUT",
    ]
    
    found_variation = None
    for variation in awaiting_scout_variations:
        if variation in status_counts:
            found_variation = variation
            print(f"\n✓ Found status '{variation}': {status_counts[variation]} records")
            break
    
    if not found_variation:
        print("\n✗ No 'Awaiting Scout' status found in any variation!")
        print("\n   Possible reasons:")
        print("   1. No records currently have this status")
        print("   2. The status might be set differently (check spelling)")
        print("   3. Records that should be 'Awaiting Scout' have a different status")
    
    # Look for records that might need Scout completion
    print("\n" + "="*80)
    print("RECORDS THAT MIGHT NEED SCOUT")
    print("="*80)
    
    # Check for specific patterns that might indicate waiting for Scout
    potential_scout_records = []
    for record in records:
        fields = record.get("fields", {})
        survey_type = fields.get("Survey Type", "")
        status = fields.get("Status", "")
        notes = fields.get("Notes", "")
        
        # Look for indicators that Scout is needed
        if "PENDING" in survey_type.upper() or "Scout" in notes or "scout" in notes:
            potential_scout_records.append({
                "id": record["id"],
                "site": fields.get("Site", "N/A"),
                "status": status,
                "survey_type": survey_type,
                "notes": notes[:100] if notes else ""
            })
    
    if potential_scout_records:
        print(f"\nFound {len(potential_scout_records)} records that might need Scout:")
        for rec in potential_scout_records[:10]:
            print(f"\n  Record {rec['id']}:")
            print(f"    Site: {rec['site']}")
            print(f"    Current Status: {rec['status']}")
            print(f"    Survey Type: {rec['survey_type']}")
            print(f"    Notes: {rec['notes']}")
        
        if len(potential_scout_records) > 10:
            print(f"\n  ... and {len(potential_scout_records) - 10} more")
    else:
        print("\nNo records found with Scout-related indicators")
    
    # Check PENDING survey types specifically
    pending_records = [r for r in records if r.get("fields", {}).get("Survey Type") == "PENDING"]
    print("\n" + "="*80)
    print("PENDING SURVEY TYPE RECORDS")
    print("="*80)
    print(f"\nFound {len(pending_records)} records with Survey Type = 'PENDING'")
    
    if pending_records:
        pending_statuses = Counter()
        for rec in pending_records:
            status = rec.get("fields", {}).get("Status", "NO_STATUS")
            pending_statuses[status] += 1
        
        print("\nStatus breakdown for PENDING survey types:")
        for status, count in sorted(pending_statuses.items(), key=lambda x: x[1], reverse=True):
            print(f"  {status:30s} : {count:4d}")
        
        # Show a few examples
        print("\nSample PENDING records:")
        for rec in pending_records[:5]:
            fields = rec.get("fields", {})
            print(f"\n  Site {fields.get('Site')}:")
            print(f"    Status: {fields.get('Status')}")
            print(f"    Notes: {fields.get('Notes', '')[:80]}")


def main():
    """Run investigation."""
    print("="*80)
    print("INVESTIGATING 'AWAITING SCOUT' STATUS")
    print("="*80)
    
    # Load token
    token = load_token()
    print("[OK] Token loaded\n")
    
    # Fetch all records
    records = fetch_all_records(token, BASE_ID, TABLE_ID)
    print(f"\n[OK] Fetched {len(records)} total records\n")
    
    # Analyze status field
    analyze_status_field(records)
    
    print("\n" + "="*80)
    print("INVESTIGATION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
