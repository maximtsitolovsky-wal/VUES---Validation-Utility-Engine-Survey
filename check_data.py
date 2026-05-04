"""Check all data sources."""
import json
from pathlib import Path

print("=" * 60)
print("DATA SOURCE CHECK")
print("=" * 60)

# Team dashboard data
with open('output/team_dashboard_data.json') as f:
    team = json.load(f)

scout = team.get('scout', {})
va = team.get('vendor_assignments', {})
vendors = va.get('vendors', [])

print("\n--- SCOUT DATA ---")
print(f"excel_total: {scout.get('excel_total')}")
print(f"completed: {scout.get('completed')}")
print(f"remaining: {scout.get('remaining')}")
print(f"completion_rate: {scout.get('completion_rate')}%")

print("\n--- VENDOR ASSIGNMENTS ---")
print(f"total_sites: {va.get('total_sites')}")
print(f"total_remaining: {va.get('total_remaining')}")
print(f"win_rate: {va.get('win_rate')}%")

print("\n--- BY VENDOR ---")
for v in vendors:
    print(f"  {v.get('vendor_name')}: assigned={v.get('total_assigned')}, completed={v.get('completed')}, remaining={v.get('remaining')}")

# Also check routing rows
with open('output/survey_routing_data.json') as f:
    routing = json.load(f)
rows = routing.get('rows', [])

print("\n--- ROUTING DATA ---")
print(f"Total rows: {len(rows)}")

# Count sites awaiting scout (no vendor yet)
awaiting_scout = [r for r in rows if not r.get('vendor')]
print(f"Sites without vendor (awaiting scout): {len(awaiting_scout)}")

# Count by survey_required status
by_survey = {}
for r in rows:
    s = r.get('survey_required', 'UNKNOWN')
    by_survey[s] = by_survey.get(s, 0) + 1
print(f"By survey_required: {by_survey}")
