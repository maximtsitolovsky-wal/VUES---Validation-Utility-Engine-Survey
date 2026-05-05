import json

with open('ui/survey_routing_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

rows = data['rows']

# Calculate per-vendor stats
vendors = {}
for r in rows:
    v = r.get('vendor') or 'unassigned'
    if v not in vendors:
        vendors[v] = {
            'total': 0,
            'no_survey': 0,
            'awaiting_scout': 0,
            'cctv': 0,
            'fa': 0,
            'both': 0,
            'complete': 0
        }
    
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

print('VENDOR SURVEY BREAKDOWN')
print('=' * 80)
for v in ['CEI', 'Wachter', 'Everon', 'PTSI', 'alarmhawaii.com']:
    if v in vendors:
        s = vendors[v]
        pending = s['cctv'] + s['fa'] + s['both']
        print(f"{v}:")
        print(f"  Total sites: {s['total']}")
        print(f"  No Survey Needed: {s['no_survey']}")
        print(f"  Awaiting Scout: {s['awaiting_scout']}")
        print(f"  Surveys Pending: {pending} (CCTV:{s['cctv']} FA:{s['fa']} BOTH:{s['both']})")
        print(f"  Completed: {s['complete']}")
        print()

# Output as JSON for the HTML
output = {
    'vendors': {},
    'totals': {
        'total': len(rows),
        'no_survey': sum(1 for r in rows if r.get('survey_required') == 'NO'),
        'awaiting_scout': sum(1 for r in rows if 'Scout not submitted' in (r.get('reason_for_decision') or '')),
        'cctv': sum(1 for r in rows if r.get('survey_type') == 'CCTV' and r.get('survey_complete') != True and 'Scout not submitted' not in (r.get('reason_for_decision') or '')),
        'fa': sum(1 for r in rows if r.get('survey_type') == 'FA/INTRUSION' and r.get('survey_complete') != True and 'Scout not submitted' not in (r.get('reason_for_decision') or '')),
        'both': sum(1 for r in rows if r.get('survey_type') == 'BOTH' and r.get('survey_complete') != True and 'Scout not submitted' not in (r.get('reason_for_decision') or '')),
        'complete': sum(1 for r in rows if r.get('survey_complete') == True)
    }
}

for v in ['CEI', 'Wachter', 'Everon', 'PTSI', 'alarmhawaii.com']:
    if v in vendors:
        s = vendors[v]
        pending = s['cctv'] + s['fa'] + s['both']
        output['vendors'][v] = {
            'total': s['total'],
            'no_survey': s['no_survey'],
            'awaiting_scout': s['awaiting_scout'],
            'pending': pending,
            'cctv': s['cctv'],
            'fa': s['fa'],
            'both': s['both'],
            'complete': s['complete']
        }

with open('ui/survey_summary_data.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2)

print("Saved to ui/survey_summary_data.json")
