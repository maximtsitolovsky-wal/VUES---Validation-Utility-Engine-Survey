import json

with open('output/team_dashboard_data.json') as f:
    data = json.load(f)

# Check vendor_assignments structure
va = data.get('vendor_assignments', {})
print('=== VENDOR_ASSIGNMENTS ===')
print(f'Keys: {list(va.keys())}')

stats = va.get('stats', [])
print(f'\nStats ({len(stats)} vendors):')
total_assigned = 0
total_completed = 0
total_remaining = 0
for v in stats:
    name = v.get('vendor_name', '?')
    assigned = v.get('total_assigned', 0)
    completed = v.get('completed', 0)
    remaining = v.get('remaining', 0)
    total_assigned += assigned
    total_completed += completed
    total_remaining += remaining
    print(f'  {name}: assigned={assigned}, completed={completed}, remaining={remaining}')

print(f'\n  VENDOR TOTALS: assigned={total_assigned}, completed={total_completed}, remaining={total_remaining}')

mesh = va.get('mesh', [])
print(f'\nMesh ({len(mesh)} rows):')
if mesh:
    # Count by status
    statuses = {}
    for m in mesh:
        status = m.get('status', 'unknown')
        statuses[status] = statuses.get(status, 0) + 1
    print('  Status breakdown:')
    for status, count in sorted(statuses.items()):
        print(f'    {status}: {count}')
    
    # Check for "loss" or similar
    loss_keywords = ['loss', 'lost', 'removed', 'cancelled', 'dropped']
    for keyword in loss_keywords:
        matches = [m for m in mesh if keyword.lower() in str(m.get('status', '')).lower()]
        if matches:
            print(f'\n  Found "{keyword}" in status: {len(matches)} rows')

# Summary stats from vendor_assignments
summary = va.get('summary', {})
print(f'\nSummary: {summary}')
