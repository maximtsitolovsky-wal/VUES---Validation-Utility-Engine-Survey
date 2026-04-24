import sys
sys.path.insert(0, 'src')
import json

from siteowlqa.vendor_assignment_tracker import VendorAssignmentTracker

# Load tracker
tracker = VendorAssignmentTracker(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Documents\BaselinePrinter\Excel\Vendor ASSIGN. 4.2.26.xlsx')
if not tracker.load_assignments():
    print("Failed to load assignments")
    exit()

print(f"Loaded {len(tracker.assignments)} assignments")

# Get Everon assignments
everon_assignments = [a for a in tracker.assignments if a.vendor_name == 'Everon']
print(f"Everon has {len(everon_assignments)} assignments")

# Load Scout completions from JSON
with open('output/team_dashboard_data.json') as f:
    data = json.load(f)

# Build completions list (as expected by tracker)
completed_submissions = []
for rec in data['scout']['records']:
    rf = rec.get('raw_fields', {})
    if rf.get('Complete?') == 1:
        site = str(rf.get('Site Number', '')).strip()
        vendor = rf.get('Surveyor Parent Company', '').strip()
        scout_date = rf.get('Scout Date', '')
        if site and vendor:
            completed_submissions.append({
                'site_number': site,
                'vendor_name': vendor,
                'submitted_at': scout_date
            })

print(f"Found {len(completed_submissions)} completed submissions")

# Check which Everon sites have completions
for ea in everon_assignments:
    for cs in completed_submissions:
        norm_site = tracker._normalize_site_number(cs['site_number'])
        if ea.site_number == norm_site:
            norm_vendor = tracker._normalize_vendor_name(cs['vendor_name'])
            print(f"  Match! Everon site {ea.site_number} was completed by {norm_vendor}")

# Now run actual calculation
stats = tracker.calculate_vendor_stats(completed_submissions)
print("\n=== Calculated Stats ===")
for vendor, s in stats.items():
    print(f"{vendor}: {s.completed}/{s.total_assigned}")
