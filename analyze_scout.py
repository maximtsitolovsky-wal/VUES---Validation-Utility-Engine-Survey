import json
from collections import Counter

with open('ui/team_dashboard_data.json', 'r') as f:
    data = json.load(f)

scout_recs = data.get('scout', {}).get('records', [])

print('=== SCOUT VARIANCE ANALYSIS ===')
print(f'Total Scout records: {len(scout_recs)}')

# Check unique site numbers
sites = [r.get('site_number') for r in scout_recs if r.get('site_number')]
unique_sites = set(sites)
print(f'Scout sites: {len(sites)} total, {len(unique_sites)} unique')
print(f'VARIANCE: {len(sites) - len(unique_sites)} duplicate site entries')

# Find sites with multiple scout visits
site_counts = Counter(sites)
multi_sites = [(site, count) for site, count in site_counts.items() if count > 1]
print(f'\nSites with >1 scout record: {len(multi_sites)}')

print('\nTop 15 sites with multiple records:')
for site, count in sorted(multi_sites, key=lambda x: -x[1])[:15]:
    print(f'  Site {site}: {count} records')

# Analyze why - check dates and vendors
print('\n=== SAMPLE MULTI-RECORD SITES ===')
for site, count in sorted(multi_sites, key=lambda x: -x[1])[:3]:
    print(f'\nSite {site} ({count} records):')
    site_recs = [r for r in scout_recs if r.get('site_number') == site]
    for r in site_recs[:5]:
        vendor = r.get('vendor_name', '?')
        date = r.get('raw_fields', {}).get('Scout Date', r.get('submitted_at', '?'))
        rec_id = r.get('record_id', '?')[:12]
        print(f'  - {vendor} | {date} | {rec_id}...')
    if count > 5:
        print(f'  ... and {count - 5} more')

# Check by vendor
print('\n=== SCOUT BY VENDOR ===')
vendor_counts = Counter(r.get('vendor_name', 'Unknown') for r in scout_recs)
for vendor, count in sorted(vendor_counts.items(), key=lambda x: -x[1]):
    print(f'{vendor}: {count}')
