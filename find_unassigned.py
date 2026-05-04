import json

with open('output/team_dashboard_data.json') as f:
    data = json.load(f)

# Vendor assignments (from Vendor ASSIGN Excel)
va = data.get('vendor_assignments', {})
mesh_data = va.get('mesh', {})
mesh_rows = mesh_data.get('rows', []) if isinstance(mesh_data, dict) else []

assigned_sites = set()
for row in mesh_rows:
    site = str(row.get('site_number', '')).strip()
    if site:
        assigned_sites.add(site)

# Scout stats says excel_total = 765
scout = data.get('scout', {})
excel_total = scout.get('excel_total', 0)

# Survey routing data
survey_routing = data.get('survey_routing', {})
routing_rows = survey_routing.get('rows', []) if isinstance(survey_routing, dict) else []

routing_sites = set()
for row in routing_rows:
    site = str(row.get('site', row.get('site_number', ''))).strip()
    if site:
        routing_sites.add(site)

print('=== DATA SOURCES ===')
print(f'Scout excel_total stat: {excel_total}')
print(f'Vendor assignments (mesh): {len(assigned_sites)} sites')
print(f'Survey routing: {len(routing_sites)} sites')

print(f'\n=== THE MATH ===')
print(f'Excel total from scout: {excel_total}')
print(f'Vendor assigned: {va.get("total_assignments")}')
print(f'Gap: {excel_total - va.get("total_assignments", 0)}')

# The 765 comes from somewhere - let me check what Excel file
# Check if there's a different source
print(f'\n=== CHECKING SCOUT SOURCE ===')
print(f'Scout stats keys: {[k for k in scout.keys() if k != "records"]}')

# Maybe the 765 is from a different Excel than vendor assignments
# Vendor assignments = 758 from "Vendor ASSIGN. 4.2.26.xlsx"
# The 765 might be from "Project Tracking" or another sheet

print(f'\nSites in routing but NOT in vendor assignments: {len(routing_sites - assigned_sites)}')
print(f'Sites in vendor assignments but NOT in routing: {len(assigned_sites - routing_sites)}')

# Find the 7 missing
diff = excel_total - va.get("total_assignments", 0)
print(f'\n=== THE {diff} MISSING SITES ===')
print('These are sites counted in excel_total (765) but not in vendor assignments (758)')

# The routing data might be the 765 source
if len(routing_sites) == 768:  # close to 765
    missing = routing_sites - assigned_sites
    print(f'\nIf routing is the source, missing sites ({len(missing)}):')
    for site in sorted(missing, key=lambda x: int(x) if x.isdigit() else 0)[:20]:
        print(f'  {site}')
    if len(missing) > 20:
        print(f'  ... and {len(missing) - 20} more')
