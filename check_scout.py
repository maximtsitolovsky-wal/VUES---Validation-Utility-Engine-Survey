#!/usr/bin/env python3
"""Check scout data discrepancy."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json

with open('ui/survey_routing_data.json') as f:
    data = json.load(f)

rows = data.get('rows', [])
print(f'Total rows: {len(rows)}')

# Count unique sites
sites = set(r.get('site') for r in rows if r.get('site'))
print(f'Unique sites: {len(sites)}')

# Count scout_submitted = True
scout_completed = [r for r in rows if r.get('scout_submitted') == True]
print(f'Scout submitted (True): {len(scout_completed)}')

# Find sites NOT scout_submitted
not_submitted = [r for r in rows if r.get('scout_submitted') != True]
print(f'Scout NOT submitted: {len(not_submitted)}')

# Check for duplicates
from collections import Counter
site_counts = Counter(r.get('site') for r in rows)
dupes = [(s, c) for s, c in site_counts.items() if c > 1]
if dupes:
    print(f'Duplicate sites: {dupes}')
else:
    print('No duplicate sites')

# Find the 1 site that's unique but not completed
scout_sites = set(r.get('site') for r in scout_completed)
all_sites = set(r.get('site') for r in rows)
missing = all_sites - scout_sites
print(f'Sites without scout: {missing}')
