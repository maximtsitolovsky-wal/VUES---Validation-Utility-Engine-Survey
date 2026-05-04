"""Check ready_to_assign for sites with scout data."""
import json

with open('output/survey_routing_data.json') as f:
    data = json.load(f)

rows = data['rows']

# Filter to sites that have scout data (scout_submitted or vendor assigned)
with_scout = [r for r in rows if r.get('scout_submitted') or r.get('vendor')]

print(f"Sites with scout data: {len(with_scout)}")

# Check ready_to_assign status
ready_yes = [r for r in with_scout if r.get('ready_to_assign') == 'YES']
ready_no = [r for r in with_scout if r.get('ready_to_assign') == 'NO']
ready_other = [r for r in with_scout if r.get('ready_to_assign') not in ('YES', 'NO')]

print(f"  Ready=YES: {len(ready_yes)}")
print(f"  Ready=NO: {len(ready_no)}")
print(f"  Ready=other: {len(ready_other)}")

# Why are some not ready?
if ready_no:
    print(f"\nSample NOT ready sites:")
    for r in ready_no[:5]:
        print(f"  Site {r['site']}: survey_required={r['survey_required']}, survey_type={r['survey_type']}, vendor={r.get('vendor','')}")

# Check pending (no scout yet)
pending = [r for r in rows if r.get('survey_required') == 'PENDING']
print(f"\nSites with PENDING survey status (awaiting scout): {len(pending)}")

# What does the survey_required field look like?
print("\nSurvey Required breakdown:")
by_status = {}
for r in rows:
    s = r.get('survey_required', 'UNKNOWN')
    by_status[s] = by_status.get(s, 0) + 1
for s, c in sorted(by_status.items(), key=lambda x: -x[1]):
    print(f"  {s}: {c}")
