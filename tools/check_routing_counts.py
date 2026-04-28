import json
from collections import Counter

d = json.load(open('ui/survey_routing_data.json'))
rows = d.get('rows', [])

print(f"Total rows: {len(rows)}")
print()

# Count by survey_type
types = Counter(r.get('survey_type', 'NONE') for r in rows)
print('By survey_type:')
for t, c in types.most_common():
    print(f'  {t}: {c}')

print()

# Count by survey_required
req = Counter(r.get('survey_required', '') for r in rows)
print('By survey_required:')
for t, c in req.most_common():
    print(f'  {t}: {c}')

print()

# Count by survey_complete
comp = Counter(str(r.get('survey_complete', False)) for r in rows)
print('By survey_complete:')
for t, c in comp.most_common():
    print(f'  {t}: {c}')

print()

# Simulate the routing page logic
# CCTV: survey_type == 'CCTV'
cctv = [r for r in rows if r.get('survey_type') == 'CCTV']
# FA: survey_type == 'FA/INTRUSION'  
fa = [r for r in rows if r.get('survey_type') == 'FA/INTRUSION']
# Both: survey_type == 'BOTH'
both = [r for r in rows if r.get('survey_type') == 'BOTH']
# No Survey: survey_required == 'NO'
no_survey = [r for r in rows if r.get('survey_required') == 'NO']
# Review: survey_type == 'REVIEW' or 'NONE'
review = [r for r in rows if r.get('survey_type') in ['REVIEW', 'NONE', None, '']]
# Complete: survey_complete == True
complete = [r for r in rows if r.get('survey_complete') == True]
# Awaiting Scout
awaiting_scout = [r for r in rows if 'No scout submission' in str(r.get('reason_for_decision', ''))]

print("Routing page categories:")
print(f"  CCTV: {len(cctv)}")
print(f"  FA/Intrusion: {len(fa)}")
print(f"  Both: {len(both)}")
print(f"  No Survey Needed: {len(no_survey)}")
print(f"  Needs Review: {len(review)}")
print(f"  Completed: {len(complete)}")
print(f"  Awaiting Scout: {len(awaiting_scout)}")
print(f"  TOTAL accounted: {len(cctv) + len(fa) + len(both) + len(no_survey) + len(review) + len(complete) + len(awaiting_scout)}")
