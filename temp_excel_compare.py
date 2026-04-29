import json
import openpyxl
import os

# Load Airtable records
d = json.load(open('ui/team_dashboard_data.json'))
records = d.get('scout', {}).get('records', [])

# Get unique sites from Airtable
airtable_sites = set(
    r.get('site_number', '').strip().lstrip('0')
    for r in records if r.get('site_number')
)

# Load Excel reference (ScoutSurveyLab.xlsm)
reference_path = r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Documents\BaselinePrinter\ScoutSurveyLab.xlsm"
wb = openpyxl.load_workbook(reference_path, read_only=True, data_only=True)
ws = wb["Scout Map Data"]
excel_sites = set(
    str(row[0].value).strip().lstrip('0')
    for row in ws.iter_rows(min_row=2, max_col=1)
    if row[0].value
)
wb.close()

# Find discrepancies
in_airtable_not_excel = airtable_sites - excel_sites
in_excel_not_airtable = excel_sites - airtable_sites
in_both = airtable_sites & excel_sites

# Count duplicates
all_site_nums = [r.get('site_number', '').strip().lstrip('0') for r in records if r.get('site_number')]
from collections import Counter
site_counts = Counter(all_site_nums)
duplicates = {s: c for s, c in site_counts.items() if c > 1}

with open('scout_excel_comparison.txt', 'w') as f:
    f.write("=" * 70 + "\n")
    f.write(" SCOUT: AIRTABLE vs EXCEL COMPARISON\n")
    f.write("=" * 70 + "\n\n")
    
    f.write(f"Total Airtable records: {len(records)}\n")
    f.write(f"Unique sites in Airtable: {len(airtable_sites)}\n")
    f.write(f"Total sites in Excel scope: {len(excel_sites)}\n")
    f.write(f"Sites in BOTH (completed): {len(in_both)}\n\n")
    
    f.write("-" * 70 + "\n")
    f.write(f" SITES IN AIRTABLE BUT NOT IN EXCEL ({len(in_airtable_not_excel)})\n")
    f.write(" (These are submitted but NOT counted as 'completed')\n")
    f.write("-" * 70 + "\n")
    if in_airtable_not_excel:
        for site in sorted(in_airtable_not_excel):
            # Find the record details
            for r in records:
                if r.get('site_number', '').strip().lstrip('0') == site:
                    vendor = r.get('vendor_name', '?')
                    submitted = r.get('submitted_at', '?')
                    f.write(f"  Site {site} | Vendor: {vendor} | Submitted: {submitted}\n")
                    break
    else:
        f.write("  (none)\n")
    
    f.write("\n" + "-" * 70 + "\n")
    f.write(f" DUPLICATE SUBMISSIONS ({len(duplicates)} sites with multiple submissions)\n")
    f.write("-" * 70 + "\n")
    for site, count in sorted(duplicates.items()):
        f.write(f"  Site {site}: {count} submissions\n")
    
    f.write("\n" + "=" * 70 + "\n")
    f.write(" SUMMARY\n")
    f.write("=" * 70 + "\n")
    f.write(f"  Total Airtable records:     {len(records)}\n")
    f.write(f"  Duplicate records:          {sum(c-1 for c in duplicates.values())}\n")
    f.write(f"  Unique sites submitted:     {len(airtable_sites)}\n")
    f.write(f"  In Excel scope (completed): {len(in_both)}\n")
    f.write(f"  NOT in Excel (out of scope):{len(in_airtable_not_excel)}\n")
    f.write(f"  Excel sites remaining:      {len(in_excel_not_airtable)}\n")
