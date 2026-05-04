#!/usr/bin/env python3
"""Diagnose why Survey Routing updates aren't working."""

import requests
import json
from pathlib import Path

# Load config
config = json.loads(Path.home().joinpath('.siteowlqa/config.json').read_text())
TOKEN = config['scout_airtable_token']
BASE_ID = config['scout_airtable_base_id']
TABLE_NAME = 'Survey Routing'

# IMPORTANT: Use table ID directly, not table name with view
TABLE_ID = 'tbl4LbgPUluSrbG2K'

headers = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json'
}

print("=" * 60)
print("  SURVEY ROUTING UPDATE DIAGNOSTIC")
print("=" * 60)

# Load routing data
print("\n1. Loading local routing data from ui/survey_routing_data.json...")
try:
    data = json.load(open('ui/survey_routing_data.json'))
    rows = data.get('rows', [])
    print(f"   [OK] Loaded {len(rows)} rows")
    
    # Sample sites
    sample_sites = [r.get('site') for r in rows[:5]]
    print(f"   Sample sites: {sample_sites}")
except Exception as e:
    print(f"   [ERR] ERROR: {e}")
    exit(1)

# Build lookup by site
site_data = {str(r['site']).strip(): r for r in rows}
print(f"   Unique sites in JSON: {len(site_data)}")

# Fetch Airtable records using TABLE ID (not name with view filter issues)
print(f"\n2. Fetching Airtable records from {BASE_ID}/{TABLE_ID}...")
all_records = []
offset = None

while True:
    url = f'https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}'
    params = {'pageSize': 100}
    if offset:
        params['offset'] = offset
    
    resp = requests.get(url, headers=headers, params=params)
    if not resp.ok:
        print(f"   [ERR] ERROR: {resp.status_code} - {resp.text}")
        break
    
    result = resp.json()
    all_records.extend(result.get('records', []))
    offset = result.get('offset')
    if not offset:
        break

print(f"   [OK] Found {len(all_records)} Airtable records")

# Check site format in Airtable
airtable_sites = [rec['fields'].get('Site', '') for rec in all_records[:10]]
print(f"   Sample Airtable sites: {airtable_sites}")

# Check for matching sites
print("\n3. Checking site matching...")
matched = 0
unmatched_airtable = []
unmatched_json = []

airtable_site_set = set()
for rec in all_records:
    site = str(rec['fields'].get('Site', '')).strip()
    airtable_site_set.add(site)
    if site in site_data:
        matched += 1
    else:
        if len(unmatched_airtable) < 5:
            unmatched_airtable.append(site)

for site in site_data.keys():
    if site not in airtable_site_set:
        if len(unmatched_json) < 5:
            unmatched_json.append(site)

print(f"   Matched sites: {matched} / {len(all_records)}")
print(f"   Unmatched Airtable (sample): {unmatched_airtable}")
print(f"   Unmatched JSON (sample): {unmatched_json}")

# Check what fields exist
print("\n4. Checking Airtable field structure...")
if all_records:
    sample = all_records[0]['fields']
    print(f"   Fields present: {list(sample.keys())}")

# Try to identify status mapping issues
def get_real_status(row):
    """Derive real status from row data."""
    if row.get('survey_complete') == True:
        return 'Completed'
    
    schedule = row.get('schedule_status', '')
    ready = row.get('ready_to_assign', '')
    survey_req = row.get('survey_required', '')
    reason = row.get('reason_for_decision', '')
    
    if survey_req == 'NO':
        return 'No Survey Needed'
    if 'No scout submission' in str(reason):
        return 'Awaiting Scout'
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

print("\n5. Checking status transitions...")
need_update = 0
no_change = 0
status_changes = {}

for rec in all_records:
    site = str(rec['fields'].get('Site', '')).strip()
    row = site_data.get(site, {})
    
    if not row:
        continue
    
    current_status = rec['fields'].get('Status', '')
    new_status = get_real_status(row)
    
    if current_status != new_status:
        need_update += 1
        key = f"{current_status} -> {new_status}"
        status_changes[key] = status_changes.get(key, 0) + 1
    else:
        no_change += 1

print(f"   Records needing update: {need_update}")
print(f"   Records already correct: {no_change}")

if status_changes:
    print("\n   Status transitions:")
    for change, count in sorted(status_changes.items(), key=lambda x: -x[1])[:10]:
        print(f"     {change}: {count}")

# Test write capability with a single record
print("\n6. Testing write capability...")
if all_records:
    test_rec = all_records[0]
    test_id = test_rec['id']
    test_site = test_rec['fields'].get('Site', '')
    current_notes = test_rec['fields'].get('Notes', '') or ''
    
    # Add/remove a test marker
    if '[TEST]' in current_notes:
        new_notes = current_notes.replace('[TEST]', '').strip()
    else:
        new_notes = f"[TEST] {current_notes}".strip()
    
    print(f"   Attempting to update record {test_id} (Site: {test_site})...")
    
    resp = requests.patch(
        f'https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}',
        headers=headers,
        json={
            'records': [{
                'id': test_id,
                'fields': {'Notes': new_notes}
            }]
        }
    )
    
    if resp.ok:
        print(f"   [OK] Write test PASSED! (toggled [TEST] marker in Notes)")
        # Restore original
        requests.patch(
            f'https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}',
            headers=headers,
            json={'records': [{'id': test_id, 'fields': {'Notes': current_notes}}]}
        )
        print(f"   [OK] Restored original Notes")
    else:
        print(f"   [ERR] Write test FAILED: {resp.status_code} - {resp.text}")

print("\n" + "=" * 60)
print("  DIAGNOSIS COMPLETE")
print("=" * 60)
