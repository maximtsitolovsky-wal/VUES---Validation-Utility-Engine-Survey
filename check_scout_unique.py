#!/usr/bin/env python3
"""Check scout unique sites discrepancy."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json

with open('ui/team_dashboard_data.json') as f:
    data = json.load(f)

scout = data.get('scout', {})
records = scout.get('records', [])

print(f"Total records: {len(records)}")
print(f"Completed (from JSON): {scout.get('completed')}")
print(f"Total submissions: {scout.get('total_submissions')}")
print(f"Unique submissions: {scout.get('unique_submissions')}")

# Find unique sites
sites = set()
for r in records:
    site = r.get('site') or r.get('Site') or r.get('site_number') or r.get('Site Number')
    if site:
        sites.add(str(site).strip())

print(f"Unique sites in records: {len(sites)}")

# Check for duplicate site numbers
from collections import Counter
site_list = []
for r in records:
    site = r.get('site') or r.get('Site') or r.get('site_number') or r.get('Site Number')
    if site:
        site_list.append(str(site).strip())

counts = Counter(site_list)
dupes = [(s, c) for s, c in counts.items() if c > 1]
print(f"Duplicate sites: {len(dupes)}")
if dupes:
    print(f"Examples: {dupes[:5]}")

# Count completed status
completed_count = 0
for r in records:
    status = r.get('status') or r.get('Status') or r.get('completion_status')
    if status and 'complete' in str(status).lower():
        completed_count += 1
print(f"Records with 'complete' status: {completed_count}")
