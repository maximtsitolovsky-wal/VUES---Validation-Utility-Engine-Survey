import json

d = json.load(open('ui/survey_routing_data.json'))
rows = d.get('rows', [])

print(f"Total rows: {len(rows)}")
print()

# Simulate getStatus function from routing.html
def get_status(row):
    if row.get('survey_complete') == True:
        return 'survey-completed'
    if row.get('survey_required') == 'NO':
        return 'full-upgrade'
    
    reason = row.get('reason_for_decision', '') or ''
    has_scout = 'No scout submission' not in reason
    
    if not has_scout:
        return 'scout-in-progress'
    
    if row.get('vues_submitted') == True:
        return 'survey-in-progress'
    
    return 'scout-completed'

# Calculate categories EXACTLY as routing.html does
cctv_data = [r for r in rows if r.get('survey_type') == 'CCTV' and r.get('survey_required') == 'YES']
fa_data = [r for r in rows if r.get('survey_type') == 'FA/INTRUSION' and r.get('survey_required') == 'YES']
upgrade_data = [r for r in rows if r.get('survey_type') == 'BOTH' and r.get('survey_required') == 'YES']
review_data = [r for r in rows if r.get('survey_type') == 'REVIEW' or (r.get('upgrade_decision') or '').find('REVIEW') >= 0]
no_survey_data = [r for r in rows if r.get('survey_required') == 'NO']

scout_data = [r for r in rows if get_status(r) in ['scout-in-progress', 'scout-completed']]
complete_data = [r for r in rows if get_status(r) == 'survey-completed']

print("=== ROUTING PAGE CATEGORIES (as coded) ===")
print(f"  CCTV (survey_type=CCTV & required=YES): {len(cctv_data)}")
print(f"  FA/Intrusion (survey_type=FA & required=YES): {len(fa_data)}")
print(f"  Both Surveys (survey_type=BOTH & required=YES): {len(upgrade_data)}")
print(f"  Needs Review (survey_type=REVIEW or upgrade has REVIEW): {len(review_data)}")
print(f"  No Survey Needed (required=NO): {len(no_survey_data)}")
print(f"  Scout (status scout-in-progress or scout-completed): {len(scout_data)}")
print(f"  Completed (status survey-completed): {len(complete_data)}")
print()

# Count by status
from collections import Counter
statuses = Counter(get_status(r) for r in rows)
print("=== STATUS BREAKDOWN ===")
for s, c in statuses.most_common():
    print(f"  {s}: {c}")

print()
print("=== THE PROBLEM ===")
print(f"Total in categories: {len(cctv_data) + len(fa_data) + len(upgrade_data) + len(review_data) + len(no_survey_data)}")
print(f"But many rows appear in MULTIPLE categories!")
print()

# Check for REVIEW rows that are also in scout_data
review_and_scout = [r for r in review_data if r in scout_data]
print(f"Rows in BOTH review_data AND scout_data: {len(review_and_scout)}")

# Rows with survey_required = 'REVIEW' (not YES or NO)
req_review = [r for r in rows if r.get('survey_required') == 'REVIEW']
print(f"Rows with survey_required='REVIEW': {len(req_review)}")
