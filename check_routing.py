"""Check routing data integrity."""
import json
from pathlib import Path

# Load routing data
routing_file = Path('output/survey_routing_data.json')
with open(routing_file) as f:
    data = json.load(f)

rows = data.get('rows', [])
summary = data.get('summary', {})

print("=" * 50)
print("ROUTING DATA CHECK")
print("=" * 50)

# Unique sites
sites = set(str(r.get('site', '')) for r in rows)
print(f"Total rows: {len(rows)}")
print(f"Unique sites: {len(sites)}")
print()

# Summary stats
print("SUMMARY:")
for k, v in summary.items():
    print(f"  {k}: {v}")
print()

# Vendor breakdown
print("BY VENDOR:")
vendors = {}
for r in rows:
    v = r.get('vendor') or '(No Vendor)'
    vendors[v] = vendors.get(v, 0) + 1
for v, count in sorted(vendors.items(), key=lambda x: -x[1]):
    print(f"  {v}: {count}")
print()

# Ready to assign
ready = [r for r in rows if r.get('ready_to_assign') == True]
not_ready = [r for r in rows if r.get('ready_to_assign') != True]
print(f"Ready to assign: {len(ready)}")
print(f"Not ready: {len(not_ready)}")

# Sample not ready reasons
if not_ready[:5]:
    print("\nSample NOT ready rows:")
    for r in not_ready[:5]:
        print(f"  Site {r.get('site')}: ready_to_assign={r.get('ready_to_assign')}, vendor={r.get('vendor')}, survey_required={r.get('survey_required')}")
