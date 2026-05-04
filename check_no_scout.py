"""Check sites WITHOUT completed scouts."""
import json
import sys
sys.path.insert(0, 'src')
from siteowlqa.survey_routing import _derive_status

data = json.load(open('ui/survey_routing_data.json'))
no_scout = [r for r in data['rows'] if not r['scout_submitted']]

statuses = {}
for r in no_scout:
    s = _derive_status(r)
    statuses[s] = statuses.get(s, 0) + 1

print(f'Total sites WITHOUT completed scouts: {len(no_scout)}')
print('\nDerived statuses for these sites:')
for status, count in sorted(statuses.items(), key=lambda x: x[1], reverse=True):
    print(f'  {status}: {count}')

# Show examples
print('\n--- EXAMPLES ---')
for status in sorted(set(statuses.keys())):
    examples = [r for r in no_scout if _derive_status(r) == status][:2]
    print(f'\n{status} examples:')
    for ex in examples:
        print(f"  Site {ex['site']}: vendor={ex['vendor']}, survey_req={ex['survey_required']}, schedule={ex['schedule_status']}, ready={ex['ready_to_assign']}")
