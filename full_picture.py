#!/usr/bin/env python3
"""Full Airtable vs Excel comparison."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import openpyxl
from pathlib import Path

# Load Airtable scout records
with open('ui/team_dashboard_data.json') as f:
    data = json.load(f)

scout = data.get('scout', {})
records = scout.get('records', [])

airtable_sites = set(
    r.get('site_number', '').strip().lstrip('0')
    for r in records if r.get('site_number')
)

# Load Excel reference
reference_path = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Documents\BaselinePrinter\ScoutSurveyLab.xlsm")
wb = openpyxl.load_workbook(reference_path, read_only=True, data_only=True)
ws = wb["Scout Map Data"]
excel_sites = set(
    str(row[0].value).strip().lstrip('0')
    for row in ws.iter_rows(min_row=2, max_col=1)
    if row[0].value
)
wb.close()

# Full picture
both = airtable_sites & excel_sites
only_airtable = airtable_sites - excel_sites
only_excel = excel_sites - airtable_sites

print("=" * 50)
print("FULL PICTURE: Airtable vs Excel")
print("=" * 50)
print(f"Airtable submissions (unique sites): {len(airtable_sites)}")
print(f"Excel scope (target sites):          {len(excel_sites)}")
print()
print(f"IN BOTH (completed):                 {len(both)}")
print(f"Only in Airtable (out of scope):     {len(only_airtable)}")
print(f"Only in Excel (not yet submitted):   {len(only_excel)}")
print()
print("=" * 50)
print("THE MATH:")
print("=" * 50)
print(f"unique_submissions should be:        {len(airtable_sites)}")
print(f"completed should be:                 {len(both)}")
print(f"Difference:                          {len(airtable_sites) - len(both)}")
print()
if only_airtable:
    print(f"Out-of-scope sites (in Airtable, not Excel):")
    for s in sorted(only_airtable, key=lambda x: int(x) if x.isdigit() else 0):
        print(f"  - {s}")
