#!/usr/bin/env python3
"""Update Airtable routing records with real status values."""

import requests
import json
import time
from pathlib import Path

# Load config
config = json.loads(Path.home().joinpath('.siteowlqa/config.json').read_text())
TOKEN = config['scout_airtable_token']
BASE_ID = config['scout_airtable_base_id']
TABLE_NAME = 'Survey Routing'

headers = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json'
}

# Load routing data
print("Loading routing data...")
data = json.load(open('ui/survey_routing_data.json'))
rows = data.get('rows', [])
print(f"Loaded {len(rows)} rows")

# Build lookup by site
site_data = {str(r['site']): r for r in rows}

# Fetch all Airtable records
print("\nFetching Airtable records...")
all_records = []
offset = None

while True:
    url = f'https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}'
    params = {'pageSize': 100}
    if offset:
        params['offset'] = offset
    
    resp = requests.get(url, headers=headers, params=params)
    if not resp.ok:
        print(f"Error: {resp.text}")
        break
    
    result = resp.json()
    all_records.extend(result.get('records', []))
    offset = result.get('offset')
    if not offset:
        break

print(f"Found {len(all_records)} Airtable records")

# Determine real status for each row
def get_real_status(row):
    """Derive real status from row data."""
    if row.get('survey_complete') == True:
        return 'Completed'
    
    schedule = row.get('schedule_status', '')
    ready = row.get('ready_to_assign', '')
    survey_req = row.get('survey_required', '')
    reason = row.get('reason_for_decision', '')
    
    # No survey needed
    if survey_req == 'NO':
        return 'No Survey Needed'
    
    # Awaiting scout
    if 'No scout submission' in str(reason):
        return 'Awaiting Scout'
    
    # Based on schedule status
    if schedule == 'REVIEW':
        return 'Needs Review'
    elif schedule == 'ON TRACK':
        if ready == 'YES':
            return 'Ready to Assign'
        else:
            return 'In Progress'
    elif schedule == 'NOT REQUIRED':
        return 'No Survey Needed'
    
    return 'Pending'

# Update records in batches
print("\nUpdating Airtable records with real statuses...")
updates = []
for rec in all_records:
    site = rec['fields'].get('Site', '')
    row = site_data.get(site, {})
    
    if not row:
        continue
    
    real_status = get_real_status(row)
    current_status = rec['fields'].get('Status', '')
    
    if real_status != current_status:
        updates.append({
            'id': rec['id'],
            'fields': {
                'Status': real_status,
                'Survey Type': row.get('survey_type', ''),
                'Notes': row.get('notes', '') or row.get('vendor_instructions', ''),
            }
        })

print(f"Records to update: {len(updates)}")

# Update in batches of 10
BATCH_SIZE = 10
updated = 0
errors = 0

for i in range(0, len(updates), BATCH_SIZE):
    batch = updates[i:i+BATCH_SIZE]
    
    resp = requests.patch(
        f'https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}',
        headers=headers,
        json={'records': batch}
    )
    
    if resp.ok:
        updated += len(batch)
        print(f"  Updated {updated}/{len(updates)} ({100*updated//len(updates)}%)")
    else:
        errors += len(batch)
        print(f"  Error: {resp.text[:100]}")
    
    time.sleep(0.25)  # Rate limiting

print(f"\nDone! Updated: {updated}, Errors: {errors}")

# Show status distribution
print("\nNew status distribution:")
from collections import Counter
statuses = Counter(get_real_status(site_data.get(rec['fields'].get('Site', ''), {})) for rec in all_records)
for s, c in statuses.most_common():
    print(f"  {s}: {c}")
