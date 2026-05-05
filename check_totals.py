import json
with open('ui/survey_routing_data.json', 'r') as f:
    data = json.load(f)

rows = data['rows']

# Verify totals
complete = [r for r in rows if r.get('survey_complete') == True]
no_survey = [r for r in rows if r.get('survey_complete') != True and r.get('survey_required') == 'NO']

print(f'Total sites: {len(rows)}')
print(f'No survey needed: {len(no_survey)}')
print(f'Survey target (need survey): {len(rows) - len(no_survey)}')
print(f'Completed: {len(complete)}')

# Per vendor
vendors = {}
for r in rows:
    v = r.get('vendor', 'unknown')
    if v not in vendors:
        vendors[v] = {'total': 0, 'no_survey': 0, 'complete': 0, 'pending': 0}
    vendors[v]['total'] += 1
    if r.get('survey_complete') == True:
        vendors[v]['complete'] += 1
    elif r.get('survey_required') == 'NO':
        vendors[v]['no_survey'] += 1
    else:
        vendors[v]['pending'] += 1

print()
for v in ['CEI', 'Wachter', 'Everon', 'PTSI', 'alarmhawaii.com']:
    s = vendors.get(v, {})
    target = s.get('total', 0) - s.get('no_survey', 0)
    print(f'{v}: total={s.get("total",0)} no_survey={s.get("no_survey",0)} target={target} complete={s.get("complete",0)} pending={s.get("pending",0)}')
