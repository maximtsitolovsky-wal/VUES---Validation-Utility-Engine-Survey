import json

with open('output/team_dashboard_data.json') as f:
    data = json.load(f)

va = data.get('vendor_assignments', {})
print('=== VENDOR_ASSIGNMENTS ===')
print(f'configured: {va.get("configured")}')
print(f'total_assignments: {va.get("total_assignments")}')
print(f'total_completed: {va.get("total_completed")}')
print(f'total_remaining: {va.get("total_remaining")}')
print(f'error: {va.get("error")}')

vendors = va.get('vendors', [])
print(f'\nVendors ({len(vendors)}):')
total_assigned = 0
total_completed = 0
total_remaining = 0
for v in vendors:
    if isinstance(v, dict):
        name = v.get('vendor_name', v.get('name', '?'))
        assigned = v.get('total_assigned', v.get('assigned', 0))
        completed = v.get('completed', 0)
        remaining = v.get('remaining', 0)
        total_assigned += assigned
        total_completed += completed
        total_remaining += remaining
        print(f'  {name}: assigned={assigned}, completed={completed}, remaining={remaining}')
    else:
        print(f'  (not a dict): {v}')

print(f'\n  VENDOR TOTALS: assigned={total_assigned}, completed={total_completed}, remaining={total_remaining}')

mesh = va.get('mesh', [])
print(f'\nMesh: {mesh[:5]}...' if len(mesh) > 5 else f'Mesh: {mesh}')

# Now the KEY question - what's shown in the UI?
scout = data.get('scout', {})
print('\n=== SCOUT STATS (what UI should show) ===')
print(f'Excel total: {scout.get("excel_total")}')
print(f'Completed: {scout.get("completed")}')
print(f'Remaining: {scout.get("remaining")}')

print('\n=== THE DISCREPANCY ===')
print(f'Scout remaining: {scout.get("remaining")}')
print(f'Vendor total_remaining: {va.get("total_remaining")}')
print(f'Difference: {scout.get("remaining", 0) - va.get("total_remaining", 0)}')
