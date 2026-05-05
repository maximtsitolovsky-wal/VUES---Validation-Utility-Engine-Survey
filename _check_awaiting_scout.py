#!/usr/bin/env python
"""Check survey routing data and awaiting scout count."""
import sys
sys.path.insert(0, 'src')

from siteowlqa.config import load_config
from siteowlqa.survey_routing import build_survey_routing_data, fetch_scout_data, load_schedule_data

cfg = load_config()
token = cfg.scout_airtable_token or cfg.airtable_token

print("=== FETCHING DATA ===")
scout_records = fetch_scout_data(token)
print(f"Scout records fetched: {len(scout_records)}")

schedule_records = load_schedule_data()
print(f"Schedule records loaded: {len(schedule_records)}")

print("\n=== BUILDING ROUTING DATA ===")
data = build_survey_routing_data(token)

print("\n=== SUMMARY ===")
s = data['summary']
print(f"Total sites: {s['total_sites']}")
print(f"Pending scout (awaiting): {s.get('pending_scout', 'N/A')}")
print(f"Surveys required: {s['surveys_required']}")
print(f"Surveys complete: {s['surveys_complete']}")
print(f"Ready to assign: {s['ready_to_assign']}")

print("\n=== VENDOR BREAKDOWN ===")
for v, stats in sorted(data['vendor_breakdown'].items()):
    print(f"  {v:12s}: total={stats['total']:3d}, survey_req={stats['survey_required']:3d}, pending={stats['pending']:3d}, complete={stats['complete']:3d}")

# Check for mismatch
awaiting_scout = s.get('pending_scout', 0)
print(f"\n=== ANALYSIS ===")
print(f"Sites with scout data: {len(scout_records)}")
print(f"Sites on schedule: {len(schedule_records)}")
print(f"Awaiting scout count: {awaiting_scout}")

if awaiting_scout == 0 and len(schedule_records) > len(scout_records):
    print("\n[WARNING] Awaiting scout is 0 but schedule has more sites than scout!")
    print(f"  Schedule sites: {len(schedule_records)}")
    print(f"  Scout sites: {len(scout_records)}")
    print(f"  Difference: {len(schedule_records) - len(scout_records)} sites may be missing scout data")
