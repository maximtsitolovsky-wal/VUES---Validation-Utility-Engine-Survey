import json

with open('output/team_dashboard_data.json') as f:
    data = json.load(f)

# Get sites from vendor assignments mesh
va = data.get('vendor_assignments', {})
mesh_data = va.get('mesh', {})
mesh_rows = mesh_data.get('rows', []) if isinstance(mesh_data, dict) else []

assigned_sites = set()
for row in mesh_rows:
    site = row.get('site_number')
    if site:
        assigned_sites.add(str(site))

print(f'Sites in vendor assignments: {len(assigned_sites)}')

# Get sites from scout records (completed)
scout = data.get('scout', {})
scout_recs = scout.get('records', [])
completed_sites = set()
for rec in scout_recs:
    site = rec.get('site_number')
    if site:
        completed_sites.add(str(site))

print(f'Sites completed (scout records): {len(completed_sites)}')

# Now we need to check the Excel master list
# It should be in the routing data or somewhere
routing = data.get('routing', {})
if routing:
    routing_rows = routing.get('rows', [])
    excel_sites = set(str(r.get('site', r.get('site_number', ''))) for r in routing_rows if r.get('site') or r.get('site_number'))
    print(f'Sites in routing data: {len(excel_sites)}')

# Check what sites are NOT assigned
not_assigned = completed_sites - assigned_sites
print(f'\nCompleted but NOT in vendor assignments: {len(not_assigned)}')
if not_assigned:
    print(f'  Sites: {sorted(not_assigned)[:20]}...')

# The 7 orphaned sites would be in Excel but not in vendor assignments
print('\n=== SUMMARY ===')
print(f'Excel total (from scout stats): {scout.get("excel_total")} sites')
print(f'Vendor assignments total: {va.get("total_assignments")} sites')
print(f'Gap: {scout.get("excel_total", 0) - va.get("total_assignments", 0)} sites NEVER ASSIGNED')
