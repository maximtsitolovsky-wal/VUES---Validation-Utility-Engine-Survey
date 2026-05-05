import json

with open('ui/survey_routing_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

cei_fix = ['1590', '2646', '3072', '864', '9']
fixed = 0

for row in data['rows']:
    site_id = str(row.get('site'))
    if site_id in cei_fix:
        row['scout_submitted'] = True
        row['schedule_status'] = 'COMPLETE'
        row['survey_type'] = 'BOTH'
        row['survey_required'] = 'YES'
        fixed += 1
        print(f"Fixed site {site_id}")

print(f"Total fixed: {fixed}")

with open('ui/survey_routing_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print("Saved!")
