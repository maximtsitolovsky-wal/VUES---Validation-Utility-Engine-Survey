import json

with open('ui/survey_routing_data.json', 'r') as f:
    data = json.load(f)

sites_to_fix = ['864', '2646', '9']
fixed = 0

for r in data['rows']:
    if str(r.get('site')) in sites_to_fix:
        r['scout_submitted'] = True
        r['reason_for_decision'] = 'CEI - BOTH surveys required'
        fixed += 1
        print(f"Fixed site {r.get('site')}: scout_submitted=True")

with open('ui/survey_routing_data.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f"\nFixed {fixed} sites. Saved!")
