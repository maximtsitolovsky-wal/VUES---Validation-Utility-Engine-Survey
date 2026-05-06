"""Get all unique site numbers from Scout Submissions table."""

import sys
import time
from pathlib import Path
from typing import Any
import requests

# Add the project's src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from siteowlqa.user_config import load_user_config

# Airtable configuration
AIRTABLE_API_BASE = "https://api.airtable.com/v0"
BASE_ID = "appAwgaX89x0JxG3Z"
TABLE_ID = "Submissions"
RATE_LIMIT_DELAY = 0.2


def fetch_all_records(token: str) -> list[dict[str, Any]]:
    """Fetch all records from the Scout submissions table."""
    url = f"{AIRTABLE_API_BASE}/{BASE_ID}/{TABLE_ID}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    all_records = []
    params = {"pageSize": 100}
    
    while True:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        records = data.get("records", [])
        all_records.extend(records)
        
        offset = data.get("offset")
        if not offset:
            break
        
        params["offset"] = offset
        time.sleep(RATE_LIMIT_DELAY)
    
    return all_records


def main():
    """Extract unique site numbers."""
    user_config = load_user_config()
    
    if not user_config:
        print("ERROR: Failed to load user config")
        return
    
    token = user_config.scout_airtable_token or user_config.airtable_token
    
    # Fetch all records
    records = fetch_all_records(token)
    
    # Extract unique site numbers
    site_numbers = set()
    for record in records:
        fields = record.get("fields", {})
        site_num = fields.get("Site Number", "")
        if site_num:
            site_numbers.add(str(site_num).strip())
    
    # Sort and print
    sorted_sites = sorted(site_numbers, key=lambda x: int(x) if x.isdigit() else x)
    
    print(f"# {len(sorted_sites)} unique site numbers from Scout Submissions")
    print()
    for site in sorted_sites:
        print(site)


if __name__ == "__main__":
    main()
