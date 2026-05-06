#!/usr/bin/env python3
"""Find incomplete scout sites."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json

with open('ui/team_dashboard_data.json') as f:
    data = json.load(f)

scout = data.get('scout', {})
records = scout.get('records', [])

# Check what fields exist
if records:
    print("Sample record keys:", list(records[0].keys())[:15])
    print()

# Find sites and their completion status
# Scout completion might be based on specific fields being filled
incomplete = []
for r in records:
    site = r.get('site') or r.get('Site') or r.get('site_number', 'Unknown')
    
    # Check if critical fields are empty
    # These are typical scout completion indicators
    check_fields = ['cabling_type', 'cable_type', 'notification_device_count', 'Camera', 'FA']
    
    missing = []
    for field in check_fields:
        val = r.get(field)
        if val is None or str(val).strip() == '':
            missing.append(field)
    
    if missing:
        incomplete.append({'site': site, 'missing': missing})

print(f"Records missing key fields: {len(incomplete)}")
if incomplete[:5]:
    for item in incomplete[:5]:
        print(f"  Site {item['site']}: missing {item['missing']}")
