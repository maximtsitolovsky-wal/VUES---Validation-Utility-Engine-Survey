"""Check derived status for sites with completed scouts."""
import json
import sys
sys.path.insert(0, 'src')
from siteowlqa.survey_routing import _derive_status

data = json.load(open('ui/survey_routing_data.json'))
scout_complete = [r for r in data['rows'] if r['scout_submitted']]

statuses = {}
for r in scout_complete:
    s = _derive_status(r)
    statuses[s] = statuses.get(s, 0) + 1

print(f'Total sites with completed scouts: {len(scout_complete)}')
print('\nDerived statuses for these sites:')
for status, count in sorted(statuses.items(), key=lambda x: x[1], reverse=True):
    print(f'  {status}: {count}')

# Show examples of each status
print('\n--- EXAMPLES ---')
for status in sorted(set(statuses.keys())):
    examples = [r for r in scout_complete if _derive_status(r) == status][:2]
    print(f'\n{status} examples:')
    for ex in examples:
        print(f"  Site {ex['site']}: vendor={ex['vendor']}, survey_req={ex['survey_required']}, schedule={ex['schedule_status']}, days={ex['days_to_construction']}")
