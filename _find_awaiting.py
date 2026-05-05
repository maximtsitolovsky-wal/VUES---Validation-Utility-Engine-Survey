#!/usr/bin/env python
"""Find the 3 CEI sites that should be BOTH but are awaiting scout."""
import json

with open('ui/survey_routing_data.json') as f:
    data = json.load(f)

# Find CEI sites that are awaiting scout
awaiting = []
for r in data['rows']:
    if r['vendor'] == 'CEI' and 'Scout not submitted' in r.get('reason_for_decision', ''):
        awaiting.append({
            'site': r['site'],
            'vendor': r['vendor'],
            'survey_type': r['survey_type'],
            'reason': r['reason_for_decision'][:50]
        })

print(f'CEI sites awaiting scout: {len(awaiting)}')
print()
for a in awaiting[:30]:
    print(f"  Site {a['site']}: {a['survey_type']} - {a['reason']}")

# Save to file
with open('_awaiting_cei.txt', 'w') as f:
    f.write(f'CEI sites awaiting scout: {len(awaiting)}\n\n')
    for a in awaiting:
        f.write(f"Site {a['site']}: {a['survey_type']}\n")

print()
print('Saved to _awaiting_cei.txt')
