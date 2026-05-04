import json
import openpyxl
from pathlib import Path

# Load the Scout Map Data Excel (source of the 765)
scout_map_path = Path.home() / "OneDrive - Walmart Inc" / "Documents" / "BaselinePrinter" / "Excel" / "2027 Survey Lab.xlsm"

print(f'Loading Scout Map Data from: {scout_map_path}')
print(f'Exists: {scout_map_path.exists()}')

if scout_map_path.exists():
    wb = openpyxl.load_workbook(scout_map_path, read_only=True, data_only=True)
    print(f'Sheets: {wb.sheetnames}')
    
    if "Scout Map Data" in wb.sheetnames:
        ws = wb["Scout Map Data"]
        scout_map_sites = set()
        for row in ws.iter_rows(min_row=2, max_col=1):
            if row[0].value:
                site = str(row[0].value).strip().lstrip("0")
                scout_map_sites.add(site)
        wb.close()
        print(f'Sites in Scout Map Data: {len(scout_map_sites)}')
    else:
        print('Sheet "Scout Map Data" not found')
        wb.close()
        scout_map_sites = set()
else:
    print('Excel file not found, trying dashboard data')
    scout_map_sites = set()

# Load vendor assignments from dashboard data
with open('output/team_dashboard_data.json') as f:
    data = json.load(f)

va = data.get('vendor_assignments', {})
mesh_data = va.get('mesh', {})
mesh_rows = mesh_data.get('rows', []) if isinstance(mesh_data, dict) else []

assigned_sites = set()
for row in mesh_rows:
    site = str(row.get('site_number', '')).strip().lstrip("0")
    if site:
        assigned_sites.add(site)

print(f'Sites in Vendor Assignments: {len(assigned_sites)}')

# Find the gap
if scout_map_sites:
    unassigned = scout_map_sites - assigned_sites
    print(f'\n=== {len(unassigned)} SITES IN SCOUT MAP BUT NOT ASSIGNED ===')
    for site in sorted(unassigned, key=lambda x: int(x) if x.isdigit() else 0):
        print(f'  Site {site}')
