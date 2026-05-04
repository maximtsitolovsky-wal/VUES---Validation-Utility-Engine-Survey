"""Check new routing data."""
import json

with open('output/survey_routing_data.json') as f:
    d = json.load(f)

s = d['summary']
print("=" * 50)
print("NEW ROUTING DATA SUMMARY")
print("=" * 50)
print(f"Total sites: {s.get('total_sites')}")
print(f"Surveys required: {s.get('surveys_required')}")
print(f"Reviews required: {s.get('review_required')}")
print(f"Ready to assign: {s.get('ready_to_assign')}")
print(f"Pending scout: {s.get('pending_scout')}")
print(f"Surveys complete: {s.get('surveys_complete')}")

rows = d['rows']
by_req = {}
for r in rows:
    status = r.get('survey_required', 'UNKNOWN')
    by_req[status] = by_req.get(status, 0) + 1
print(f"\nRow breakdown by survey_required: {by_req}")

ready_yes = sum(1 for r in rows if r.get('ready_to_assign') == 'YES')
ready_no = sum(1 for r in rows if r.get('ready_to_assign') == 'NO')
print(f"Ready=YES: {ready_yes}")
print(f"Ready=NO: {ready_no}")

# Check PENDING specifically
pending = [r for r in rows if r.get('survey_required') == 'PENDING']
print(f"\nPENDING sites (awaiting scout): {len(pending)}")
