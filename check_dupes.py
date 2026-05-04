import json
from collections import Counter

with open('ui/team_dashboard_data.json', 'r') as f:
    data = json.load(f)

scout_recs = data.get('scout', {}).get('records', [])

# Get ALL sites with counts
sites = [r.get('site_number') for r in scout_recs if r.get('site_number')]
site_counts = Counter(sites)
all_dupes = [(site, count) for site, count in site_counts.items() if count > 1]

print(f'Total scout records: {len(scout_recs)}')
print(f'Unique sites: {len(set(sites))}')
print(f'ACTUAL DUPLICATE SITES: {len(all_dupes)}')
print(f'Total extra records (variance): {sum(c-1 for s,c in all_dupes)}')

print(f'\nALL {len(all_dupes)} DUPLICATE SITES:')
for site, count in sorted(all_dupes, key=lambda x: -x[1]):
    recs = [r for r in scout_recs if r.get('site_number') == site]
    vendor = recs[0].get('vendor_name', '?')
    email = recs[0].get('vendor_email', '?')
    print(f'  Site {site}: {count} records | {vendor} | {email}')
