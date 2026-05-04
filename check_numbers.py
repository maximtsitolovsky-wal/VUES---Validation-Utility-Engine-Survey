import json

with open('output/team_dashboard_data.json') as f:
    data = json.load(f)

scout = data.get('scout', {})
vendors = data.get('vendors', [])

print('=== SCOUT DATA ===')
print(f'Total records: {len(scout.get("records", []))}')
print(f'Unique sites: {scout.get("unique_sites", "?")}')
print(f'Completed: {scout.get("completed", "?")}')
print(f'Excel total: {scout.get("excel_total", "?")}')
print(f'Remaining: {scout.get("remaining", "?")}')

print('\n=== VENDOR STATS ===')
total_assigned = 0
total_completed = 0
total_remaining = 0
for v in vendors:
    name = v.get('vendor_name', '?')
    assigned = v.get('total_assigned', 0)
    completed = v.get('completed', 0)
    remaining = v.get('remaining', 0)
    total_assigned += assigned
    total_completed += completed
    total_remaining += remaining
    print(f'{name}: assigned={assigned}, completed={completed}, remaining={remaining}')

print(f'\nTOTALS: assigned={total_assigned}, completed={total_completed}, remaining={total_remaining}')
print(f'Math check: {total_assigned} - {total_completed} = {total_assigned - total_completed}')

# Check for discrepancies
scout_recs = scout.get('records', [])
scout_sites = set(r.get('site_number') for r in scout_recs if r.get('site_number'))
print(f'\nScout unique site numbers in records: {len(scout_sites)}')

# Check vendor mesh for losses
mesh = data.get('vendor_mesh', [])
if mesh:
    losses = [m for m in mesh if m.get('status') == 'loss' or m.get('loss')]
    print(f'\nVendor mesh total: {len(mesh)}')
    print(f'Losses in mesh: {len(losses)}')
