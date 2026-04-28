#!/usr/bin/env python3
"""Check real status values in routing data."""

import json
from collections import Counter
from pathlib import Path

data = json.load(open('ui/survey_routing_data.json'))
rows = data.get('rows', [])

print(f"Total rows: {len(rows)}")
print()

# Check all unique status values
statuses = Counter(r.get('status', '') for r in rows)
print('Status values:')
for s, c in statuses.most_common():
    print(f'  "{s or "(empty)"}": {c}')

print()

# Check schedule_status
sched = Counter(r.get('schedule_status', '') for r in rows)
print('Schedule status values:')
for s, c in sched.most_common():
    print(f'  "{s or "(empty)"}": {c}')

print()

# Check survey_complete
complete = Counter(str(r.get('survey_complete', '')) for r in rows)
print('Survey complete values:')
for s, c in complete.most_common():
    print(f'  {s}: {c}')

print()

# Check scout_submitted  
scout = Counter(str(r.get('scout_submitted', '')) for r in rows)
print('Scout submitted values:')
for s, c in scout.most_common():
    print(f'  {s}: {c}')

print()

# Sample a few rows to see all fields
print("Sample row fields:")
if rows:
    r = rows[0]
    for k, v in r.items():
        print(f"  {k}: {v}")
