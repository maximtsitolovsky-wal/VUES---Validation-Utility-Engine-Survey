#!/usr/bin/env python3
"""Check Airtable tables."""

import requests
import json
from pathlib import Path

config = json.loads(Path.home().joinpath('.siteowlqa/config.json').read_text())
TOKEN = config['scout_airtable_token']
BASE_ID = config['scout_airtable_base_id']

print(f"Using base: {BASE_ID}")

headers = {'Authorization': f'Bearer {TOKEN}'}

# Try to read from various tables
tables_to_try = ['Survey Routing', 'Routing', 'Submissions']
for table in tables_to_try:
    try:
        url = f'https://api.airtable.com/v0/{BASE_ID}/{table}'
        print(f"\nTrying: {table}")
        resp = requests.get(url, headers=headers, params={'maxRecords': 1})
        print(f"  Status: {resp.status_code}")
        if resp.ok:
            records = resp.json().get('records', [])
            print(f"  Found {len(records)} record(s)")
            if records:
                print(f"  Fields: {list(records[0].get('fields', {}).keys())[:5]}...")
        else:
            print(f"  Error: {resp.text[:100]}")
    except Exception as e:
        print(f"  Exception: {e}")
