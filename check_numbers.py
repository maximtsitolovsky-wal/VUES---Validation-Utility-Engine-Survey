import json

with open('output/team_dashboard_data.json') as f:
    data = json.load(f)

print('Top-level keys:', list(data.keys()))

scout = data.get('scout', {})
print('\n=== SCOUT STATS ===')
for k, v in scout.items():
    if k != 'records':
        print(f'  {k}: {v}')

print(f'\n  records count: {len(scout.get("records", []))}')

# Check vendor_stats
vendor_stats = data.get('vendor_stats', [])
print(f'\n=== VENDOR_STATS ({len(vendor_stats)} vendors) ===')
total_assigned = 0
total_completed = 0
total_remaining = 0
for v in vendor_stats:
    name = v.get('vendor_name', v.get('name', '?'))
    assigned = v.get('total_assigned', v.get('assigned', 0))
    completed = v.get('completed', 0)
    remaining = v.get('remaining', 0)
    total_assigned += assigned
    total_completed += completed
    total_remaining += remaining
    print(f'  {name}: assigned={assigned}, completed={completed}, remaining={remaining}')

print(f'\n  TOTALS: assigned={total_assigned}, completed={total_completed}, remaining={total_remaining}')

# Check vendor_mesh for losses
vendor_mesh = data.get('vendor_mesh', [])
print(f'\n=== VENDOR_MESH ({len(vendor_mesh)} rows) ===')
if vendor_mesh:
    # Count by status
    statuses = {}
    for m in vendor_mesh:
        status = m.get('status', 'unknown')
        statuses[status] = statuses.get(status, 0) + 1
    print('  Status breakdown:')
    for status, count in sorted(statuses.items()):
        print(f'    {status}: {count}')

# The key question: why 110 remaining vs 103?
print('\n=== THE MATH ===')
excel_total = scout.get('excel_total', 0)
completed = scout.get('completed', 0)
remaining = scout.get('remaining', 0)
print(f'Excel total: {excel_total}')
print(f'Completed (from scout stats): {completed}')
print(f'Remaining (from scout stats): {remaining}')
print(f'Excel - Completed = {excel_total} - {completed} = {excel_total - completed}')

# Count unique completed sites from records
scout_recs = scout.get('records', [])
completed_sites = set(r.get('site_number') for r in scout_recs if r.get('site_number'))
print(f'\nUnique sites in scout records: {len(completed_sites)}')
print(f'Difference (records vs completed stat): {len(completed_sites)} vs {completed} = {len(completed_sites) - completed}')
