"""
CEI Assignment Analysis Script
Analyzes survey routing data for CEI assignment creation
"""
import json
from collections import defaultdict

# Load the survey routing data
with open('ui/survey_routing_data.json', 'r') as f:
    data = json.load(f)

# Get all rows
rows = data['rows']

# Define CEI vendors (original CEI + Techwise + SAS)
cei_vendors = {'CEI', 'Techwise', 'SAS'}

# Filter for CEI-related sites
cei_sites = [r for r in rows if r.get('vendor', '').strip() in cei_vendors]

# Count by original vendor
vendor_counts = defaultdict(int)
for site in cei_sites:
    vendor_counts[site.get('vendor', 'Unknown')] += 1

print("=" * 70)
print("CEI ASSIGNMENT ANALYSIS")
print("=" * 70)
print(f"\nGenerated from: {data.get('generated_at', 'Unknown')}")
print(f"\n{'='*70}")
print("VENDOR CONSOLIDATION CHECK")
print("=" * 70)
print(f"\nOriginal CEI sites:  {vendor_counts.get('CEI', 0)}")
print(f"Techwise sites:      {vendor_counts.get('Techwise', 0)} (expected: 78)")
print(f"SAS sites:           {vendor_counts.get('SAS', 0)} (expected: 8)")
print(f"\nTOTAL CEI (consolidated): {len(cei_sites)}")

# Now analyze survey requirements for CEI sites
# Filter for sites that require surveys
cei_survey_required = [r for r in cei_sites if r.get('survey_required', '').upper() == 'YES']

print(f"\n{'='*70}")
print("CEI SITES REQUIRING SURVEYS: {0}".format(len(cei_survey_required)))
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

# Check schedule_status for "awaiting scout" or similar
awaiting_scout = []
complete = []
pending_assignment = []

for site in cei_survey_required:
    status = site.get('schedule_status', '').upper().strip()
    survey_complete = site.get('survey_complete', False)
    
    if survey_complete:
        complete.append(site)
    elif 'AWAITING' in status or 'PENDING SCOUT' in status or 'SCOUT' in status:
        awaiting_scout.append(site)
    else:
        pending_assignment.append(site)

# Also check scout_submitted field
no_scout = [r for r in cei_survey_required if not r.get('scout_submitted', True)]

print(f"\n{'='*70}")
print("SURVEY TYPE BREAKDOWN (CEI Sites Requiring Surveys)")
print("=" * 70)
print(f"\n1. CCTV ONLY surveys:        {len(cctv_only)}")
print(f"2. FA/INTRUSION ONLY surveys: {len(fa_only)}")
print(f"3. BOTH surveys needed:       {len(both_surveys)}")
if unknown_type:
    print(f"   Unknown/Other types:       {len(unknown_type)}")
    # Show unique types
    unique_types = set(r.get('survey_type', 'BLANK') for r in unknown_type)
    print(f"   (Types: {unique_types})")

print(f"\n{'='*70}")
print("SCHEDULE STATUS BREAKDOWN (CEI Sites)")
print("=" * 70)

# Count by schedule_status
status_counts = defaultdict(int)
for site in cei_survey_required:
    status = site.get('schedule_status', 'UNKNOWN')
    status_counts[status] += 1

for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
    print(f"   {status:30} : {count}")

print(f"\n{'='*70}")
print("ASSIGNMENT READINESS (CEI Sites)")
print("=" * 70)

# Check survey_complete field
already_complete = [r for r in cei_survey_required if r.get('survey_complete', False)]
# Check awaiting scout (scout_submitted = False)
awaiting_scout_real = [r for r in cei_survey_required if not r.get('scout_submitted', True) and not r.get('survey_complete', False)]
# Ready to assign (scout submitted, not complete)
ready_to_assign = [r for r in cei_survey_required if r.get('scout_submitted', True) and not r.get('survey_complete', False)]

print(f"\n4. Awaiting Scout (can't assign yet): {len(awaiting_scout_real)}")
print(f"5. Already COMPLETE:                  {len(already_complete)}")
print(f"   READY TO ASSIGN:                   {len(ready_to_assign)}")

print(f"\n{'='*70}")
print("DETAILED BREAKDOWN: Ready to Assign by Survey Type")
print("=" * 70)

# Ready to assign by survey type
ready_cctv = [r for r in ready_to_assign if r.get('survey_type', '').upper() == 'CCTV']
ready_fa = [r for r in ready_to_assign if r.get('survey_type', '').upper() in ['FA/INTRUSION', 'FA/INTRUSION ONLY', 'FA INTRUSION']]
ready_both = [r for r in ready_to_assign if r.get('survey_type', '').upper() in ['BOTH', 'CCTV + FA/INTRUSION']]

print(f"\n   CCTV surveys ready:        {len(ready_cctv)}")
print(f"   FA/INTRUSION ready:        {len(ready_fa)}")
print(f"   BOTH surveys ready:        {len(ready_both)}")

# Cross-tabulation: Survey Type x Schedule Status
print(f"\n{'='*70}")
print("CROSS-TAB: Survey Type x Schedule Status (CEI)")
print("=" * 70)

# Build cross-tab
cross_tab = defaultdict(lambda: defaultdict(int))
for site in cei_survey_required:
    survey_type = site.get('survey_type', 'UNKNOWN')
    status = site.get('schedule_status', 'UNKNOWN')
    cross_tab[survey_type][status] += 1

# Get all unique statuses
all_statuses = sorted(set(site.get('schedule_status', 'UNKNOWN') for site in cei_survey_required))

# Print header
print(f"\n{'Survey Type':25} | ", end="")
for status in all_statuses:
    print(f"{status[:12]:>12} | ", end="")
print("TOTAL")
print("-" * (28 + 15 * len(all_statuses) + 8))

# Print rows
for survey_type in sorted(cross_tab.keys()):
    print(f"{survey_type:25} | ", end="")
    row_total = 0
    for status in all_statuses:
        count = cross_tab[survey_type][status]
        row_total += count
        print(f"{count:>12} | ", end="")
    print(f"{row_total:>5}")

# Print totals row
print("-" * (28 + 15 * len(all_statuses) + 8))
print(f"{'TOTAL':25} | ", end="")
grand_total = 0
for status in all_statuses:
    col_total = sum(cross_tab[st][status] for st in cross_tab)
    grand_total += col_total
    print(f"{col_total:>12} | ", end="")
print(f"{grand_total:>5}")

print(f"\n{'='*70}")
print("SUMMARY FOR CEI ASSIGNMENT CREATION")
print("=" * 70)
print(f"""
┌─────────────────────────────────────────────────────────────────────┐
│  TOTAL CEI SITES (incl. Techwise + SAS): {len(cei_sites):>4}                        │
│  ─────────────────────────────────────────                          │
│    Original CEI:  {vendor_counts.get('CEI', 0):>4}                                          │
│    Techwise:      {vendor_counts.get('Techwise', 0):>4}  (expected 78)                             │
│    SAS:           {vendor_counts.get('SAS', 0):>4}  (expected 8)                              │
├─────────────────────────────────────────────────────────────────────┤
│  SURVEY REQUIREMENTS                                                │
│  ─────────────────────────────────────────                          │
│  1. CCTV surveys needed:        {len(cctv_only):>4}                                 │
│  2. FA/INTRUSION surveys:       {len(fa_only):>4}                                 │
│  3. BOTH surveys needed:        {len(both_surveys):>4}                                 │
├─────────────────────────────────────────────────────────────────────┤
│  ASSIGNMENT STATUS                                                  │
│  ─────────────────────────────────────────                          │
│  4. Awaiting Scout (can't assign): {len(awaiting_scout_real):>4}                             │
│  5. Already COMPLETE:              {len(already_complete):>4}                             │
│     READY TO ASSIGN:               {len(ready_to_assign):>4}                             │
└─────────────────────────────────────────────────────────────────────┘
""")

# List sites awaiting scout
if awaiting_scout_real:
    print(f"\n{'='*70}")
    print("SITES AWAITING SCOUT (Cannot Assign Yet)")
    print("=" * 70)
    for site in sorted(awaiting_scout_real, key=lambda x: x.get('site', '')):
        print(f"   Site {site.get('site'):>6} | {site.get('survey_type'):20} | {site.get('schedule_status')}")
