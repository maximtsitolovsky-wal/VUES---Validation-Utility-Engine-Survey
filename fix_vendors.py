import json

with open('ui/survey_routing_data.json', 'r') as f:
    data = json.load(f)

# Fix the 5 sites with missing vendors
fixes = {
    '2070': 'PTSI',
    '2071': 'PTSI', 
    '2188': 'PTSI',
    '2308': 'alarmhawaii.com',
    '3883': 'alarmhawaii.com'
}

fixed = 0
for r in data['rows']:
    site = str(r.get('site'))
    if site in fixes:
        r['vendor'] = fixes[site]
        r['survey_type'] = 'BOTH'
        r['survey_required'] = 'YES'
        r['reason_for_decision'] = f'{fixes[site]} - BOTH surveys required'
        fixed += 1
        print(f'Fixed site {site}: vendor={fixes[site]}')

with open('ui/survey_routing_data.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f'\nFixed {fixed} sites. Saved!')
