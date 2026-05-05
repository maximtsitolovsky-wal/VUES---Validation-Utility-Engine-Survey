import json

with open('ui/survey_routing_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

rows = data['rows']

# Recalculate everything exactly like routing.html does
complete = [r for r in rows if r.get('survey_complete') == True]
not_complete = [r for r in rows if r.get('survey_complete') != True]

no_survey = [r for r in not_complete if r.get('survey_required') == 'NO']
needs_survey = [r for r in not_complete if r.get('survey_required') != 'NO']

awaiting_scout = [r for r in needs_survey if 'Scout not submitted' in (r.get('reason_for_decision') or '')]
has_scout = [r for r in needs_survey if 'Scout not submitted' not in (r.get('reason_for_decision') or '')]

cctv = [r for r in has_scout if r.get('survey_type') == 'CCTV']
fa = [r for r in has_scout if r.get('survey_type') == 'FA/INTRUSION']
both = [r for r in has_scout if r.get('survey_type') == 'BOTH']

print("=== MUTUALLY EXCLUSIVE BREAKDOWN (matches routing.html) ===")
print(f"Total rows: {len(rows)}")
print(f"Completed: {len(complete)}")
print(f"No Survey: {len(no_survey)}")
print(f"Awaiting Scout: {len(awaiting_scout)}")
print(f"CCTV: {len(cctv)}")
print(f"FA: {len(fa)}")
print(f"BOTH: {len(both)}")
total = len(complete) + len(no_survey) + len(awaiting_scout) + len(cctv) + len(fa) + len(both)
print(f"SUM: {total} {'OK' if total == len(rows) else 'MISMATCH'}")

# Update summary to match
data['summary']['total_sites'] = len(rows)
data['summary']['surveys_complete'] = len(complete)
data['summary']['surveys_required'] = len(needs_survey) + len(complete)  # All that need survey (done or not)
data['summary']['pending_scout'] = len(awaiting_scout)
data['summary']['pending_type'] = len(awaiting_scout)
data['summary']['cctv_surveys'] = len(cctv)
data['summary']['fa_surveys'] = len(fa)
data['summary']['both_surveys'] = len(both)

# Vendor breakdown
vendor_stats = {}
for r in rows:
    v = r.get('vendor') or 'unassigned'
    if v not in vendor_stats:
        vendor_stats[v] = {'total': 0, 'survey_required': 0, 'pending': 0, 'complete': 0}
    vendor_stats[v]['total'] += 1
    if r.get('survey_required') == 'YES':
        vendor_stats[v]['survey_required'] += 1
        if r.get('survey_complete') == True:
            vendor_stats[v]['complete'] += 1
        else:
            vendor_stats[v]['pending'] += 1

data['summary']['vendor_breakdown'] = vendor_stats

with open('ui/survey_routing_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print("\n=== UPDATED SUMMARY ===")
print(f"pending_scout: {data['summary']['pending_scout']}")
print(f"both_surveys: {data['summary']['both_surveys']}")
print(f"surveys_complete: {data['summary']['surveys_complete']}")
