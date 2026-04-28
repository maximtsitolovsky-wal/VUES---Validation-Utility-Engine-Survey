#!/usr/bin/env python3
"""Import routing data into Airtable Survey Routing table."""

import requests
import json
import time
from pathlib import Path

# Load config
config = json.loads(Path.home().joinpath('.siteowlqa/config.json').read_text())
TOKEN = config['scout_airtable_token']
BASE_ID = config['scout_airtable_base_id']
TABLE_NAME = 'Survey Routing'

print(f"Base: {BASE_ID}")
print(f"Table: {TABLE_NAME}")

headers = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json'
}

# Test access
print("\nTesting access...")
resp = requests.get(
    f'https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}',
    headers=headers,
    params={'maxRecords': 1}
)
print(f"Status: {resp.status_code}")

if not resp.ok:
    print(f"Error: {resp.text}")
    exit(1)

print("Table accessible!")
existing = len(resp.json().get('records', []))
print(f"Existing records: {existing}")

# Load routing data
print("\nLoading routing data from JSON...")
routing_data = json.loads(Path('ui/survey_routing_data.json').read_text())
rows = routing_data.get('rows', [])
print(f"Rows to import: {len(rows)}")

if existing > 0:
    print("\nTable already has data. Skipping import to avoid duplicates.")
    print("If you want to reimport, clear the table first.")
    exit(0)

# Map JSON fields to Airtable fields
def map_row(row):
    """Map routing JSON row to Airtable fields."""
    # Determine status from various fields
    status = row.get('status', '')
    if not status:
        if row.get('survey_complete') == 'Yes':
            status = 'Completed'
        elif row.get('scout_submitted') == 'Yes':
            status = 'Scout Done'
        else:
            status = 'Needs Review'
    
    # Map survey type
    survey_type = row.get('survey_type', '')
    if 'BOTH' in survey_type.upper():
        survey_type = 'BOTH'
    elif 'CCTV' in survey_type.upper():
        survey_type = 'CCTV'
    elif 'FA' in survey_type.upper() or 'INTRUSION' in survey_type.upper():
        survey_type = 'FA/INTRUSION'
    else:
        survey_type = 'NONE'
    
    return {
        'Site': str(row.get('site', '')),
        'Vendor': row.get('vendor', ''),
        'Status': status,
        'Survey Type': survey_type,
        'Survey Required': row.get('survey_required', '').upper() == 'YES',
        'Notes': row.get('notes', '') or row.get('reason_for_decision', ''),
        'Days to Construction': int(row.get('days_to_construction', 0) or 0) if str(row.get('days_to_construction', '')).isdigit() else None,
    }

# Import in batches of 10 (Airtable limit)
BATCH_SIZE = 10
total = len(rows)
imported = 0
errors = 0

print(f"\nImporting {total} rows in batches of {BATCH_SIZE}...")

for i in range(0, total, BATCH_SIZE):
    batch = rows[i:i+BATCH_SIZE]
    records = [{'fields': map_row(row)} for row in batch]
    
    resp = requests.post(
        f'https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}',
        headers=headers,
        json={'records': records}
    )
    
    if resp.ok:
        imported += len(batch)
        print(f"  Imported {imported}/{total} ({100*imported//total}%)")
    else:
        errors += len(batch)
        print(f"  Error at batch {i//BATCH_SIZE}: {resp.text[:100]}")
    
    # Rate limiting: max 5 requests per second
    time.sleep(0.25)

print(f"\nDone! Imported: {imported}, Errors: {errors}")
