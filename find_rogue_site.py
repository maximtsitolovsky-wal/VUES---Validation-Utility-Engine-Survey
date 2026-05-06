#!/usr/bin/env python3
"""Find scout sites that aren't in Excel reference."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import openpyxl
from pathlib import Path

# Load scout records
with open('ui/team_dashboard_data.json') as f:
    data = json.load(f)

scout = data.get('scout', {})
records = scout.get('records', [])

# Get unique sites from Airtable
airtable_sites = set(
    r.get('site_number', '').strip().lstrip('0')
    for r in records if r.get('site_number')
)
print(f"Unique Airtable sites: {len(airtable_sites)}")

# Load Excel reference
reference_path = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Documents\BaselinePrinter\ScoutSurveyLab.xlsm")
if not reference_path.exists():
    print(f"Excel not found: {reference_path}")
    sys.exit(1)

wb = openpyxl.load_workbook(reference_path, read_only=True, data_only=True)
ws = wb["Scout Map Data"]
excel_stores = set(
    str(row[0].value).strip().lstrip('0')
    for row in ws.iter_rows(min_row=2, max_col=1)
    if row[0].value
)
wb.close()
print(f"Excel reference sites: {len(excel_stores)}")

# Find the difference
in_airtable_not_excel = airtable_sites - excel_stores
in_excel_not_airtable = excel_stores - airtable_sites

print(f"\nSites in Airtable but NOT in Excel ({len(in_airtable_not_excel)}):")
for site in sorted(in_airtable_not_excel, key=lambda x: int(x) if x.isdigit() else 0):
    print(f"  - Site {site}")

print(f"\nCompleted (intersection): {len(airtable_sites & excel_stores)}")
