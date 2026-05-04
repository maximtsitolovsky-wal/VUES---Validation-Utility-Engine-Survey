import json

with open('output/team_dashboard_data.json') as f:
    data = json.load(f)

# Get sites from vendor assignments
va = data.get('vendor_assignments', {})
mesh_data = va.get('mesh', {})
mesh_rows = mesh_data.get('rows', []) if isinstance(mesh_data, dict) else []

assigned_sites = set()
for row in mesh_rows:
    site = str(row.get('site_number', '')).strip()
    if site:
        assigned_sites.add(site)

print(f'Sites in vendor assignments: {len(assigned_sites)}')

# Get sites from Excel (survey_routing has the master list)
survey_routing = data.get('survey_routing', {})
routing_rows = survey_routing.get('rows', []) if isinstance(survey_routing, dict) else []

excel_sites = set()
for row in routing_rows:
    site = str(row.get('site', row.get('site_number', ''))).strip()
    if site:
        excel_sites.add(site)

print(f'Sites in Excel/routing: {len(excel_sites)}')

# Find sites in Excel but NOT in vendor assignments
unassigned = excel_sites - assigned_sites
print(f'\n=== {len(unassigned)} SITES IN EXCEL BUT NEVER ASSIGNED ===')
for site in sorted(unassigned, key=lambda x: int(x) if x.isdigit() else 0):
    print(f'  Site {site}')

# Also check the reverse - assigned but not in Excel
extra_assigned = assigned_sites - excel_sites
if extra_assigned:
    print(f'\n=== {len(extra_assigned)} SITES ASSIGNED BUT NOT IN EXCEL ===')
    for site in sorted(extra_assigned, key=lambda x: int(x) if x.isdigit() else 0):
        print(f'  Site {site}')
