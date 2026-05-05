import json

with open('ui/survey_routing_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total rows: {len(data['rows'])}")

updated = 0
sites_updated = []

for row in data['rows']:
    vendor = row.get('vendor', '')
    if not vendor or vendor.strip() == '':
        sites_updated.append(row.get('site'))
        row['vendor'] = 'CEI'
        row['assigned_vendor'] = 'CEI'
        row['survey_type'] = 'BOTH'
        row['survey_required'] = 'YES'
        row['upgrade_decision'] = 'FULL UPGRADE - ASSIGNED TO CEI'
        row['reason_for_decision'] = 'Outlier site assigned to CEI for full survey coverage'
        row['ready_to_assign'] = 'YES'
        row['assigned'] = True
        updated += 1

print(f"Sites updated: {sites_updated}")
print(f"Total updated: {updated}")

# Update summary
if updated > 0:
    data['summary']['vendor_breakdown']['CEI']['total'] += updated
    data['summary']['vendor_breakdown']['CEI']['survey_required'] += updated
    data['summary']['vendor_breakdown']['CEI']['pending'] += updated
    data['summary']['vendor_breakdown']['unassigned'] = {'total': 0, 'survey_required': 0, 'pending': 0, 'complete': 0}
    data['summary']['no_vendor'] = 0

    with open('ui/survey_routing_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print("File saved!")
else:
    print("No changes needed")
