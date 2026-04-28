#!/usr/bin/env python3
"""Check Airtable tables and create Survey Routing table if needed."""

import requests
import json
from pathlib import Path

# Load config
config_path = Path.home() / ".siteowlqa" / "config.json"
config = json.loads(config_path.read_text())

TOKEN = config.get('scout_airtable_token', '')
BASE_ID = config.get('scout_airtable_base_id', '')

print(f"Base ID: {BASE_ID}")
print(f"Token: {TOKEN[:20]}...")

headers = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json'
}

# List tables
print("\nFetching tables...")
resp = requests.get(
    f'https://api.airtable.com/v0/meta/bases/{BASE_ID}/tables',
    headers=headers
)
print(f"Status: {resp.status_code}")

if resp.ok:
    tables = resp.json().get('tables', [])
    print(f"\nTables in base ({len(tables)}):")
    for t in tables:
        print(f"  - {t['name']} (id: {t['id']})")
else:
    print(f"Error: {resp.text[:500]}")
