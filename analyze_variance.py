import json
from collections import Counter

with open('ui/team_dashboard_data.json', 'r') as f:
    data = json.load(f)

survey_recs = data.get('survey', {}).get('records', [])
scout_recs = data.get('scout', {}).get('records', [])

print('=== SUBMISSION ANALYSIS ===')
print(f'Survey records: {len(survey_recs)}')
print(f'Scout records: {len(scout_recs)}')
print(f'Total records: {len(survey_recs) + len(scout_recs)}')

# Check for duplicate submission IDs in survey
survey_ids = [r.get('submission_id') or r.get('record_id') for r in survey_recs]
unique_survey_ids = set(survey_ids)
print(f'\nSurvey unique IDs: {len(unique_survey_ids)} (dupes: {len(survey_ids) - len(unique_survey_ids)})')

# Check for duplicate submission IDs in scout
scout_ids = [r.get('submission_id') or r.get('record_id') for r in scout_recs]
unique_scout_ids = set(scout_ids)
print(f'Scout unique IDs: {len(unique_scout_ids)} (dupes: {len(scout_ids) - len(unique_scout_ids)})')

# Check for duplicate site numbers in survey
survey_sites = [r.get('site_number') for r in survey_recs if r.get('site_number')]
unique_survey_sites = set(survey_sites)
print(f'\nSurvey sites: {len(survey_sites)} total, {len(unique_survey_sites)} unique')
print(f'Sites with multiple surveys: {len(survey_sites) - len(unique_survey_sites)}')

# Find which sites have multiple submissions
site_counts = Counter(survey_sites)
multi_sites = [(site, count) for site, count in site_counts.items() if count > 1]
print(f'\nSites with >1 survey submission: {len(multi_sites)}')
if multi_sites:
    print('Top 10:')
    for site, count in sorted(multi_sites, key=lambda x: -x[1])[:10]:
        print(f'  Site {site}: {count} submissions')

# Check by vendor
print('\n=== BY VENDOR ===')
vendor_counts = Counter(r.get('vendor_name', 'Unknown') for r in survey_recs)
for vendor, count in sorted(vendor_counts.items(), key=lambda x: -x[1]):
    print(f'{vendor}: {count}')

# Analyze why sites have multiple submissions
print('\n=== MULTI-SUBMISSION ANALYSIS ===')
for site, count in sorted(multi_sites, key=lambda x: -x[1])[:5]:
    print(f'\nSite {site} ({count} submissions):')
    site_recs = [r for r in survey_recs if r.get('site_number') == site]
    for r in site_recs:
        vendor = r.get('vendor_name', '?')
        status = r.get('processing_status', '?')
        date = r.get('submitted_at', '?')
        print(f'  - {vendor} | {status} | {date}')
