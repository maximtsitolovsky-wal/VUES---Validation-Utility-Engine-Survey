"""Analyze Scout submissions table for site number statistics.

This script:
1. Fetches ALL records from the Scout submissions table
2. Counts total records
3. Counts unique site numbers
4. Identifies and lists duplicate site numbers (sites with more than 1 submission)
"""

import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any
import requests

# Add the project's src directory to the path to import user_config
sys.path.insert(0, str(Path(__file__).parent / "src"))

from siteowlqa.user_config import load_user_config

# Airtable configuration
AIRTABLE_API_BASE = "https://api.airtable.com/v0"
BASE_ID = "appxLzMgjnHKDmrWi"
TABLE_ID = "tblV4M2dRFtjIyxJH"

# Rate limiting (5 requests per second per base)
RATE_LIMIT_DELAY = 0.2


def try_fetch_with_token(token: str, token_name: str) -> list[dict[str, Any]] | None:
    """Try to fetch records with a specific token."""
    url = f"{AIRTABLE_API_BASE}/{BASE_ID}/{TABLE_ID}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    params = {"pageSize": 1}  # Just test access with 1 record
    
    try:
        print(f"Trying {token_name}...")
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        print(f"[SUCCESS] {token_name} has access!\n")
        return fetch_all_records_with_token(token)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print(f"[DENIED] {token_name} does not have access to this base.\n")
            return None
        raise


def fetch_all_records_with_token(token: str) -> list[dict[str, Any]]:
    """Fetch all records from the Scout submissions table with pagination."""
    url = f"{AIRTABLE_API_BASE}/{BASE_ID}/{TABLE_ID}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    all_records = []
    params = {"pageSize": 100}
    
    print(f"Fetching records from Scout submissions table...")
    print(f"Base ID: {BASE_ID}")
    print(f"Table ID: {TABLE_ID}\n")
    
    page = 1
    while True:
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            records = data.get("records", [])
            all_records.extend(records)
            
            print(f"Page {page}: fetched {len(records)} records (total so far: {len(all_records)})")
            
            offset = data.get("offset")
            if not offset:
                break
            
            params["offset"] = offset
            page += 1
            
            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)
            
        except requests.exceptions.HTTPError as e:
            print(f"\n[ERROR] HTTP Error: {e}")
            print(f"Response: {e.response.text}")
            raise
        except Exception as e:
            print(f"\n[ERROR] Error fetching records: {e}")
            raise
    
    print(f"\n[SUCCESS] Successfully fetched {len(all_records)} total records\n")
    return all_records


def analyze_site_numbers(records: list[dict[str, Any]]) -> None:
    """Analyze site numbers and print statistics."""
    site_numbers = []
    
    # Extract site numbers from records
    for record in records:
        fields = record.get("fields", {})
        # Try common field names for site number
        site_num = (
            fields.get("Site Number") or 
            fields.get("Site") or 
            fields.get("Site #") or 
            fields.get("Store Number") or
            ""
        )
        
        if site_num:
            # Convert to string and strip whitespace
            site_num_str = str(site_num).strip()
            if site_num_str:
                site_numbers.append(site_num_str)
    
    # Count occurrences
    site_counter = Counter(site_numbers)
    
    # Statistics
    total_records = len(records)
    total_with_site_numbers = len(site_numbers)
    unique_sites = len(site_counter)
    duplicates = {site: count for site, count in site_counter.items() if count > 1}
    
    # Print results
    print("=" * 70)
    print("SCOUT SUBMISSIONS ANALYSIS")
    print("=" * 70)
    print()
    
    print(f"Total Records: {total_records}")
    print(f"Records with Site Numbers: {total_with_site_numbers}")
    print(f"Unique Site Numbers: {unique_sites}")
    print(f"Duplicate Sites (more than 1 submission): {len(duplicates)}")
    print()
    
    if duplicates:
        print("=" * 70)
        print("DUPLICATE SITE NUMBERS")
        print("=" * 70)
        print()
        print(f"{'Site Number':<20} {'Submission Count':<20}")
        print("-" * 40)
        
        # Sort by count (descending) then by site number
        for site, count in sorted(duplicates.items(), key=lambda x: (-x[1], x[0])):
            print(f"{site:<20} {count:<20}")
        
        print()
        print(f"Total duplicate sites: {len(duplicates)}")
        print(f"Total duplicate submissions: {sum(duplicates.values()) - len(duplicates)}")
    else:
        print("[OK] No duplicate site numbers found!")
    
    print()
    print("=" * 70)


def main():
    """Main function to run the analysis."""
    # Load user config from ~/.siteowlqa/config.json
    user_config = load_user_config()
    
    if not user_config:
        print("[ERROR] Failed to load user config from ~/.siteowlqa/config.json")
        print("Please run: python -m siteowlqa.setup_config")
        return
    
    print(f"Config Scout Base ID: {user_config.scout_airtable_base_id}")
    print(f"Requested Base ID: {BASE_ID}")
    print()
    
    # Try Scout token first, then main token
    tokens_to_try = []
    if user_config.scout_airtable_token:
        tokens_to_try.append((user_config.scout_airtable_token, "Scout token"))
    if user_config.airtable_token:
        tokens_to_try.append((user_config.airtable_token, "Main Airtable token"))
    
    if not tokens_to_try:
        print("[ERROR] No Airtable tokens found in user config.")
        print("Please run: python -m siteowlqa.setup_config")
        return
    
    records = None
    for token, token_name in tokens_to_try:
        records = try_fetch_with_token(token, token_name)
        if records is not None:
            break
    
    if records is None:
        print("[ERROR] Neither token has access to the specified base.")
        print(f"\nRequested: Base ID = {BASE_ID}, Table ID = {TABLE_ID}")
        if user_config.scout_airtable_base_id:
            print(f"\nDid you mean to use the configured Scout base instead?")
            print(f"  Configured Scout Base ID: {user_config.scout_airtable_base_id}")
            print(f"  Configured Scout Table: {user_config.scout_airtable_table_name}")
        return
    
    # Analyze site numbers
    try:
        analyze_site_numbers(records)
    except Exception as e:
        print(f"\n[ERROR] Analysis failed: {e}")
        return


if __name__ == "__main__":
    main()
