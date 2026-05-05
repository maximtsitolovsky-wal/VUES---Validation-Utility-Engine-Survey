"""
CEI Assignment Analysis Script - Fixed
Analyzes survey routing data for CEI assignment creation
"""
import json
from collections import defaultdict

# Load the survey routing data
with open('ui/survey_routing_data.json', 'r') as f:
    data = json.load(f)

# Get all rows
rows = data['rows']

# First, check all unique vendors in the data
print("=" * 70)
print("ALL VENDORS IN DATA")
print("=" * 70)
vendor_counts_all = defaultdict(int)
for r in rows:
    vendor = r.get('vendor', 'BLANK')
    vendor_counts_all[vendor] += 1

for vendor, count in sorted(vendor_counts_all.items(), key=lambda x: -x[1]):
    print(f"   {vendor:20} : {count}")

# Check if Techwise/SAS might be in a different field or have different casing
print("\n" + "=" * 70)
print("SEARCHING FOR TECHWISE/SAS IN ALL FIELDS")
print("=" * 70)

techwise_sites = []
sas_sites = []
for r in rows:
    row_str = json.dumps(r).upper()
    if 'TECHWISE' in row_str:
        techwise_sites.append(r)
    if 'SAS' in row_str and 'PASSES' not in row_str:  # Exclude 'passes_at_qa'
        # Check more carefully
        for key, val in r.items():
            if isinstance(val, str) and 'SAS' in val.upper() and key != 'passes_at_qa':
                sas_sites.append(r)
                break

print(f"Sites mentioning 'Techwise': {len(techwise_sites)}")
print(f"Sites mentioning 'SAS': {len(sas_sites)}")

# Define CEI vendors (original CEI + Techwise + SAS)
# Check case-insensitive
cei_vendors_lower = {'cei', 'techwise', 'sas'}
cei_sites = [r for r in rows if r.get('vendor', '').strip().lower() in cei_vendors_lower]

# Count by original vendor
vendor_counts = defaultdict(int)
for site in cei_sites:
    vendor_counts[site.get('vendor', 'Unknown')] += 1

print("\n" + "=" * 70)
print("CEI ASSIGNMENT ANALYSIS")
print("=" * 70)
print(f"\nGenerated from: {data.get('generated_at', 'Unknown')}")
print(f"\n{'='*70}")
print("VENDOR CONSOLIDATION CHECK")
print("=" * 70)
print(f"\nOriginal CEI sites:  {vendor_counts.get('CEI', 0)}")
print(f"Techwise sites:      {vendor_counts.get('Techwise', vendor_counts.get('techwise', 0))} (expected: 78)")
print(f"SAS sites:           {vendor_counts.get('SAS', vendor_counts.get('sas', 0))} (expected: 8)")
print(f"\nTOTAL CEI (consolidated): {len(cei_sites)}")

# Now analyze survey requirements for CEI sites
# Filter for sites that require surveys
cei_survey_required = [r for r in cei_sites if r.get('survey_required', '').upper() == 'YES']

print(f"\n{'='*70}")
print(f"CEI SITES REQUIRING SURVEYS: {len(cei_survey_required)}")
print("=" * 70)

# Categorize by survey_type
cctv_only = []
fa_only = []
both_surveys = []
unknown_type = []

for site in cei_survey_required:
    survey_type = site.get('survey_type', '').upper().strip()
    if survey_type == 'CCTV':
        cctv_only.append(site)
    elif survey_type in ['FA/INTRUSION', 'FA/INTRUSION ONLY', 'FA INTRUSION']:
        fa_only.append(site)
    elif survey_type in ['BOTH', 'CCTV + FA/INTRUSION', 'CCTV AND FA/INTRUSION']:
        both_surveys.append(site)
    else:
        unknown_type.append(site)

print(f"\n1. CCTV ONLY surveys:        {len(cctv_only)}")
print(f"2. FA/INTRUSION ONLY surveys: {len(fa_only)}")
print(f"3. BOTH surveys needed:       {len(both_surveys)}")
if unknown_type:
    print(f"   Unknown/Other types:       {len(unknown_type)}")
    unique_types = set(r.get('survey_type', 'BLANK') for r in unknown_type)
    print(f"   (Types: {unique_types})")

# Check survey_complete and scout_submitted fields
already_complete = [r for r in cei_survey_required if r.get('survey_complete', False)]
awaiting_scout_real = [r for r in cei_survey_required if not r.get('scout_submitted', True) and not r.get('survey_complete', False)]
ready_to_assign = [r for r in cei_survey_required if r.get('scout_submitted', True) and not r.get('survey_complete', False)]

print(f"\n{'='*70}")
print("ASSIGNMENT READINESS (CEI Sites)")
print("=" * 70)
print(f"\n4. Awaiting Scout (can't assign yet): {len(awaiting_scout_real)}")
print(f"5. Already COMPLETE:                  {len(already_complete)}")
print(f"   READY TO ASSIGN:                   {len(ready_to_assign)}")

# Schedule status breakdown
print(f"\n{'='*70}")
print("SCHEDULE STATUS BREAKDOWN (CEI Sites)")
print("=" * 70)
status_counts = defaultdict(int)
for site in cei_survey_required:
    status = site.get('schedule_status', 'UNKNOWN')
    status_counts[status] += 1

for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
    print(f"   {status:30} : {count}")

# Ready to assign by survey type
print(f"\n{'='*70}")
print("READY TO ASSIGN BY SURVEY TYPE")
print("=" * 70)
ready_cctv = [r for r in ready_to_assign if r.get('survey_type', '').upper() == 'CCTV']
ready_fa = [r for r in ready_to_assign if r.get('survey_type', '').upper() in ['FA/INTRUSION', 'FA/INTRUSION ONLY', 'FA INTRUSION']]
ready_both = [r for r in ready_to_assign if r.get('survey_type', '').upper() in ['BOTH', 'CCTV + FA/INTRUSION']]

print(f"\n   CCTV surveys ready:        {len(ready_cctv)}")
print(f"   FA/INTRUSION ready:        {len(ready_fa)}")
print(f"   BOTH surveys ready:        {len(ready_both)}")

# Cross-tabulation
print(f"\n{'='*70}")
print("CROSS-TAB: Survey Type x Schedule Status (CEI)")
print("=" * 70)

cross_tab = defaultdict(lambda: defaultdict(int))
for site in cei_survey_required:
    survey_type = site.get('survey_type', 'UNKNOWN')
    status = site.get('schedule_status', 'UNKNOWN')
    cross_tab[survey_type][status] += 1

all_statuses = sorted(set(site.get('schedule_status', 'UNKNOWN') for site in cei_survey_required))

print(f"\n{'Survey Type':25} | ", end="")
for status in all_statuses:
    print(f"{status[:12]:>12} | ", end="")
print("TOTAL")
print("-" * (28 + 15 * len(all_statuses) + 8))

for survey_type in sorted(cross_tab.keys()):
    print(f"{survey_type:25} | ", end="")
    row_total = 0
    for status in all_statuses:
        count = cross_tab[survey_type][status]
        row_total += count
        print(f"{count:>12} | ", end="")
    print(f"{row_total:>5}")

print("-" * (28 + 15 * len(all_statuses) + 8))
print(f"{'TOTAL':25} | ", end="")
grand_total = 0
for status in all_statuses:
    col_total = sum(cross_tab[st][status] for st in cross_tab)
    grand_total += col_total
    print(f"{col_total:>12} | ", end="")
print(f"{grand_total:>5}")

# Final Summary Box (ASCII safe)
print(f"\n{'='*70}")
print("SUMMARY FOR CEI ASSIGNMENT CREATION")
print("=" * 70)
print("""
+---------------------------------------------------------------------+
|  TOTAL CEI SITES (incl. Techwise + SAS): {:>4}                        |
|  -----------------------------------------                          |
|    Original CEI:  {:>4}                                              |
|    Techwise:      {:>4}  (expected 78)                               |
|    SAS:           {:>4}  (expected 8)                                |
+---------------------------------------------------------------------+
|  SURVEY REQUIREMENTS                                                |
|  -----------------------------------------                          |
|  1. CCTV surveys needed:        {:>4}                                |
|  2. FA/INTRUSION surveys:       {:>4}                                |
|  3. BOTH surveys needed:        {:>4}                                |
+---------------------------------------------------------------------+
|  ASSIGNMENT STATUS                                                  |
|  -----------------------------------------                          |
|  4. Awaiting Scout (can't assign): {:>4}                             |
|  5. Already COMPLETE:              {:>4}                             |
|     READY TO ASSIGN:               {:>4}                             |
+---------------------------------------------------------------------+
""".format(
    len(cei_sites),
    vendor_counts.get('CEI', 0),
    vendor_counts.get('Techwise', vendor_counts.get('techwise', 0)),
    vendor_counts.get('SAS', vendor_counts.get('sas', 0)),
    len(cctv_only),
    len(fa_only),
    len(both_surveys),
    len(awaiting_scout_real),
    len(already_complete),
    len(ready_to_assign)
))

# List sites awaiting scout
if awaiting_scout_real:
    print(f"\n{'='*70}")
    print("SITES AWAITING SCOUT (Cannot Assign Yet)")
    print("=" * 70)
    for site in sorted(awaiting_scout_real, key=lambda x: x.get('site', '')):
        print(f"   Site {site.get('site'):>6} | {site.get('survey_type'):20} | {site.get('schedule_status')}")
