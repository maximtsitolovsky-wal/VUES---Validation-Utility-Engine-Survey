import json
from collections import Counter

with open('ui/team_dashboard_data.json') as f:
    data = json.load(f)

scout = data.get('scout', {}).get('records', [])
sites = [r.get('site_number') for r in scout if r.get('site_number')]
dupes = [(s,c) for s,c in Counter(sites).items() if c > 1]

print(f'=== FRESH DATA (just pulled from Airtable) ===')
print(f'Scout records: {len(scout)}')
print(f'Unique sites: {len(set(sites))}')
print(f'Variance: {len(scout) - len(set(sites))}')
print(f'Duplicate sites: {len(dupes)}')

print(f'\nAll {len(dupes)} duplicates:')
for s, c in sorted(dupes, key=lambda x: -x[1]):
    recs = [r for r in scout if r.get('site_number') == s]
    v = recs[0].get('vendor_name', '?')
    print(f'  Site {s}: {c} records ({v})')
