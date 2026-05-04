"""Full breakdown of all sites and their statuses."""
import json
import sys
sys.path.insert(0, 'src')
from siteowlqa.survey_routing import _derive_status

data = json.load(open('ui/survey_routing_data.json'))
all_sites = data['rows']

print(f'=== FULL BREAKDOWN OF {len(all_sites)} SITES ===\n')

# By scout submission status
scout_complete = [r for r in all_sites if r['scout_submitted']]
no_scout = [r for r in all_sites if not r['scout_submitted']]

print(f'Sites WITH completed scouts: {len(scout_complete)}')
print(f'Sites WITHOUT completed scouts: {len(no_scout)}')
print()

# Derived statuses for ALL sites
all_statuses = {}
for r in all_sites:
    s = _derive_status(r)
    all_statuses[s] = all_statuses.get(s, 0) + 1

print('Derived statuses for ALL sites:')
for status, count in sorted(all_statuses.items(), key=lambda x: x[1], reverse=True):
    print(f'  {status}: {count}')
print()

# Ready to assign breakdown
ready = [r for r in all_sites if r['ready_to_assign'] == 'YES']
not_ready = [r for r in all_sites if r['ready_to_assign'] == 'NO']

print(f'Ready to assign: {len(ready)}')
print(f'NOT ready to assign: {len(not_ready)}')
print()

# The 108 number - where does it come from?
# Let's check different combinations
print('=== POSSIBLE SOURCES OF "108" ===')
print(f'Sites WITHOUT scout: {len(no_scout)}')
print(f'Sites with ready_to_assign=NO: {len(not_ready)}')
print(f'Sites with schedule_status=REVIEW: {len([r for r in all_sites if r["schedule_status"] == "REVIEW"])}')
print(f'Sites with schedule_status=PENDING: {len([r for r in all_sites if r["schedule_status"] == "PENDING"])}')
print(f'Sites with derived status "Needs Review": {len([r for r in all_sites if _derive_status(r) == "Needs Review"])}')
print(f'Sites with derived status "Pending": {len([r for r in all_sites if _derive_status(r) == "Pending"])}')
print(f'Sites with derived status "Awaiting Scout": {len([r for r in all_sites if _derive_status(r) == "Awaiting Scout"])}')
