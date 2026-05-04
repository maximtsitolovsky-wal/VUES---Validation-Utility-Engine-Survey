import json

with open('output/team_dashboard_data.json') as f:
    data = json.load(f)

va = data.get('vendor_assignments', {})
mesh_data = va.get('mesh', {})
mesh_rows = mesh_data.get('rows', []) if isinstance(mesh_data, dict) else []

print(f'Total mesh rows: {len(mesh_rows)}')

# Group by status
statuses = {}
for row in mesh_rows:
    status = row.get('status_key', row.get('status', 'unknown'))
    statuses[status] = statuses.get(status, 0) + 1

print('\nStatus breakdown:')
for status, count in sorted(statuses.items(), key=lambda x: -x[1]):
    print(f'  {status}: {count}')

# Check for anything that looks like "loss"
loss_rows = [r for r in mesh_rows if 'loss' in str(r).lower() or 'unassigned' in str(r).lower()]
print(f'\nRows with "loss" or "unassigned" in data: {len(loss_rows)}')

# What about "pending" or "not completed"?
pending = [r for r in mesh_rows if r.get('status_key') in ['pending', 'assigned_pending', 'not_started']]
print(f'Pending/not started: {len(pending)}')

# Check the actual remaining calculation
completed_in_mesh = len([r for r in mesh_rows if 'complete' in str(r.get('status_key', '')).lower()])
print(f'\nCompleted in mesh: {completed_in_mesh}')
print(f'Not completed in mesh: {len(mesh_rows) - completed_in_mesh}')

# ALSO check survey routing for "losses" concept
survey_routing = data.get('survey_routing', {})
if survey_routing:
    rows = survey_routing.get('rows', [])
    print(f'\n=== SURVEY ROUTING ({len(rows)} rows) ===')
    # Check for loss-related fields
    if rows:
        print(f'Sample keys: {list(rows[0].keys())[:10]}')
