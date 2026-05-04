import json

with open('output/team_dashboard_data.json') as f:
    data = json.load(f)

va = data.get('vendor_assignments', {})
mesh_data = va.get('mesh', {})
summary = mesh_data.get('summary', {}) if isinstance(mesh_data, dict) else {}

print('=== MESH SUMMARY ===')
for k, v in sorted(summary.items()):
    print(f'  {k}: {v}')

print('\n=== THE TRUTH ===')
scout = data.get('scout', {})

print(f'''
EXCEL PERSPECTIVE:
  Total sites in Excel:     {scout.get('excel_total')}
  Completed:                {scout.get('completed')}
  Remaining:                {scout.get('remaining')}

VENDOR ASSIGNMENT PERSPECTIVE:
  Total assigned:           {va.get('total_assignments')}
  Completed:                {va.get('total_completed')}
  Remaining (pending):      {va.get('total_remaining')}

THE GAP:
  Excel total - Vendor assigned = {scout.get('excel_total', 0) - va.get('total_assignments', 0)} sites NEVER ASSIGNED

LOSSES BREAKDOWN:
  matched_complete:         {summary.get('matched_complete', 0)} (wins)
  pending_assignment:       {summary.get('pending_assignment', 0)} (still need to do)
  started_not_complete:     {summary.get('started_not_complete', 0)} (in progress)
  completed_by_other_vendor:{summary.get('completed_by_other_vendor', 0)} (wrong vendor)
  unassigned_airtable:      {summary.get('unassigned_airtable', 0)} (not in Excel)
  losses_total:             {summary.get('losses_total', 0)} (sum of non-wins)

WHY THE NUMBERS DON'T MATCH:
  - "110 remaining" = Excel perspective (765 - 655 = 110)
  - "103 remaining" = Vendor perspective (758 - 655 = 103)
  - "103 losses" = pending_assignment + other issues
  - The 7-site gap = sites in Excel but NEVER assigned to vendors
''')
