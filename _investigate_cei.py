#!/usr/bin/env python
"""Investigate the 5 CEI sites showing as awaiting scout when CEI should be 342/342."""
import sys
sys.path.insert(0, 'src')

from siteowlqa.config import load_config
from siteowlqa.survey_routing import fetch_scout_data, load_schedule_data, DEFAULT_WORKBOOK_PATH

cfg = load_config()
token = cfg.scout_airtable_token or cfg.airtable_token

print("=" * 60)
print("INVESTIGATING CEI AWAITING SCOUT MISMATCH")
print("=" * 60)

# The 5 sites showing as awaiting scout for CEI
problem_sites = ['1590', '2646', '3072', '864', '9']

# Load scout data from Airtable
print("\n[1] Checking Scout Airtable for these sites...")
scout_records = fetch_scout_data(token)
scout_sites = {s.site: s for s in scout_records}

for site in problem_sites:
    if site in scout_sites:
        print(f"  Site {site}: FOUND in Scout Airtable")
    else:
        print(f"  Site {site}: NOT FOUND in Scout Airtable")

# Load schedule data from Excel
print("\n[2] Checking Excel schedule for these sites...")
schedule_records = load_schedule_data(DEFAULT_WORKBOOK_PATH)
schedule_sites = {s.site: s for s in schedule_records}

for site in problem_sites:
    if site in schedule_sites:
        s = schedule_sites[site]
        print(f"  Site {site}: In Excel as vendor={s.vendor}")
    else:
        print(f"  Site {site}: NOT in Excel schedule")

# Check CEI counts
print("\n[3] CEI Site Counts...")
cei_in_excel = [s for s in schedule_records if s.vendor == 'CEI']
cei_scouts = [s for s in scout_records if s.site in [x.site for x in cei_in_excel]]

print(f"  CEI sites in Excel: {len(cei_in_excel)}")
print(f"  CEI sites with scout in Airtable: {len(cei_scouts)}")

# Find CEI sites in Excel that DON'T have scouts
cei_sites_set = {s.site for s in cei_in_excel}
scout_sites_set = {s.site for s in scout_records}
missing_scouts = cei_sites_set - scout_sites_set

print(f"\n[4] CEI sites in Excel WITHOUT scout data ({len(missing_scouts)}):")
for site in sorted(missing_scouts):
    print(f"  {site}")

# Check if these are the Hawaii/Alaska special vendor sites
print("\n[5] Checking if problem sites are Hawaii/Alaska...")
# We don't have state data directly, but let's see if they're in the special list
print("  (Need to check state data or special vendor assignment)")

# Save results
with open('_cei_investigation.txt', 'w') as f:
    f.write("CEI Sites Awaiting Scout Investigation\n")
    f.write("=" * 50 + "\n\n")
    f.write(f"CEI sites in Excel: {len(cei_in_excel)}\n")
    f.write(f"CEI sites with scout: {len(cei_scouts)}\n")
    f.write(f"Missing scouts: {len(missing_scouts)}\n\n")
    f.write("Sites missing scout data:\n")
    for site in sorted(missing_scouts):
        f.write(f"  {site}\n")

print("\nSaved to _cei_investigation.txt")
