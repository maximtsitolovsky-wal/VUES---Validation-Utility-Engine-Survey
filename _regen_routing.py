#!/usr/bin/env python
"""Regenerate survey routing data and show analytics."""
import sys
import json
sys.path.insert(0, 'src')

from pathlib import Path
from siteowlqa.config import load_config
from siteowlqa.survey_routing import (
    refresh_survey_routing, 
    build_survey_routing_data,
    DEFAULT_WORKBOOK_PATH,
    VENDOR_REASSIGNMENT
)

print("=" * 60)
print("SURVEY ROUTING DATA REGENERATION")
print("=" * 60)

print(f"\nVendor Reassignment Config: {VENDOR_REASSIGNMENT}")

cfg = load_config()
token = cfg.scout_airtable_token or cfg.airtable_token

print("\nBuilding routing data...")
data = build_survey_routing_data(token, DEFAULT_WORKBOOK_PATH)

# Save to ui/
output_path = Path('ui/survey_routing_data.json')
with open(output_path, 'w') as f:
    json.dump(data, f, indent=2)
print(f"Saved to: {output_path}")

# Also save to output/
output_path2 = Path('output/survey_routing_data.json')
with open(output_path2, 'w') as f:
    json.dump(data, f, indent=2)
print(f"Saved to: {output_path2}")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
s = data['summary']
for k, v in s.items():
    print(f"  {k}: {v}")

print("\n" + "=" * 60)
print("VENDOR BREAKDOWN")
print("=" * 60)
for vendor, stats in sorted(data['vendor_breakdown'].items()):
    print(f"  {vendor:12s}: total={stats['total']:3d}, survey_req={stats['survey_required']:3d}, pending={stats['pending']:3d}, complete={stats['complete']:3d}")

# CEI-specific breakdown
print("\n" + "=" * 60)
print("CEI DETAILED BREAKDOWN (for assignments)")
print("=" * 60)

cei_rows = [r for r in data['rows'] if r['vendor'] == 'CEI']
print(f"Total CEI sites: {len(cei_rows)}")

# By survey type
by_type = {}
for r in cei_rows:
    st = r['survey_type']
    by_type[st] = by_type.get(st, 0) + 1

print("\nBy Survey Type:")
for st, count in sorted(by_type.items()):
    print(f"  {st:15s}: {count}")

# By status
by_status = {}
for r in cei_rows:
    st = r['schedule_status']
    by_status[st] = by_status.get(st, 0) + 1

print("\nBy Schedule Status:")
for st, count in sorted(by_status.items()):
    print(f"  {st:15s}: {count}")

# Awaiting scout
awaiting_scout = [r for r in cei_rows if 'Scout not submitted' in r.get('reason_for_decision', '')]
print(f"\nAwaiting Scout (can't assign): {len(awaiting_scout)}")

# Ready to assign
ready = [r for r in cei_rows if r['ready_to_assign'] == 'YES']
print(f"Ready to Assign: {len(ready)}")

# Complete
complete = [r for r in cei_rows if r['survey_complete'] == True]
print(f"Already Complete: {len(complete)}")

print("\n" + "=" * 60)
print("ASSIGNMENT BRESURVEY TYPE")
print("=" * 60)
ready_by_type = {}
for r in ready:
    st = r['survey_type']
    ready_by_type[st] = ready_by_type.get(st, 0) + 1

for st, count in sorted(ready_by_type.items()):
    print(f"  Ready to assign {st:15s}: {count}")
