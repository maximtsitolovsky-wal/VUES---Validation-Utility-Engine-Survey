import json
with open('ui/survey_routing_data.json', 'r') as f:
    data = json.load(f)

rows = data['rows']

vendors = {}
for r in rows:
    v = r.get('vendor', 'unknown')
    if v not in vendors:
        vendors[v] = {'total': 0, 'no_survey': 0, 'awaiting_scout': 0, 'cctv': 0, 'fa': 0, 'both': 0, 'complete': 0}
    vendors[v]['total'] += 1
    
    if r.get('survey_complete') == True:
        vendors[v]['complete'] += 1
    elif r.get('survey_required') == 'NO':
        vendors[v]['no_survey'] += 1
    elif 'Scout not submitted' in (r.get('reason_for_decision') or ''):
        vendors[v]['awaiting_scout'] += 1
    else:
        st = r.get('survey_type', '')
        if st == 'CCTV':
            vendors[v]['cctv'] += 1
        elif st == 'FA/INTRUSION':
            vendors[v]['fa'] += 1
        elif st == 'BOTH':
            vendors[v]['both'] += 1

print('EXACT CURRENT NUMBERS')
print('=' * 95)
print(f'{"Vendor":<15} {"Total":>6} {"NoSurv":>7} {"Scout":>6} {"CCTV":>5} {"FA":>5} {"Both":>5} {"Done":>5} {"Target":>7} {"Pending":>8}')
print('-' * 95)

grand = {'total': 0, 'no_survey': 0, 'awaiting_scout': 0, 'cctv': 0, 'fa': 0, 'both': 0, 'complete': 0}
for v in ['CEI', 'Wachter', 'Everon', 'PTSI', 'alarmhawaii.com']:
    s = vendors.get(v, {})
    target = s.get('total',0) - s.get('no_survey',0)
    pending = s.get('awaiting_scout',0) + s.get('cctv',0) + s.get('fa',0) + s.get('both',0)
    print(f'{v:<15} {s.get("total",0):>6} {s.get("no_survey",0):>7} {s.get("awaiting_scout",0):>6} {s.get("cctv",0):>5} {s.get("fa",0):>5} {s.get("both",0):>5} {s.get("complete",0):>5} {target:>7} {pending:>8}')
    for k in grand:
        grand[k] += s.get(k, 0)

print('-' * 95)
gtarget = grand['total'] - grand['no_survey']
gpending = grand['awaiting_scout'] + grand['cctv'] + grand['fa'] + grand['both']
print(f'{"TOTAL":<15} {grand["total"]:>6} {grand["no_survey"]:>7} {grand["awaiting_scout"]:>6} {grand["cctv"]:>5} {grand["fa"]:>5} {grand["both"]:>5} {grand["complete"]:>5} {gtarget:>7} {gpending:>8}')
print()
print('Verification: NoSurv + Scout + CCTV + FA + Both + Done = Total')
total_check = grand["no_survey"]+grand["awaiting_scout"]+grand["cctv"]+grand["fa"]+grand["both"]+grand["complete"]
print(f'              {grand["no_survey"]} + {grand["awaiting_scout"]} + {grand["cctv"]} + {grand["fa"]} + {grand["both"]} + {grand["complete"]} = {total_check}')
print()
print('Target = Total - NoSurv (sites needing surveys)')
print('Pending = Scout + CCTV + FA + Both (not yet completed)')
