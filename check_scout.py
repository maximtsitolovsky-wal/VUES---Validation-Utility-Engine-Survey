import json

with open('ui/survey_routing_data.json', 'r') as f:
    data = json.load(f)

rows = data['rows']

# Method 1: Check reason_for_decision for 'Scout not submitted'
method1 = len([r for r in rows if 'Scout not submitted' in (r.get('reason_for_decision') or '')])

# Method 2: Check scout_submitted = False  
method2 = len([r for r in rows if r.get('scout_submitted') == False])

# Method 3: routing.html logic - needs survey AND has 'Scout not submitted'
needs_survey = [r for r in rows if r.get('survey_required') != 'NO' and r.get('survey_complete') != True]
method3 = len([r for r in needs_survey if 'Scout not submitted' in (r.get('reason_for_decision') or '')])

print(f"Method 1 (reason contains 'Scout not submitted'): {method1}")
print(f"Method 2 (scout_submitted = False): {method2}")
print(f"Method 3 (needs survey + scout not submitted): {method3}")
print(f"Summary field pending_scout: {data['summary'].get('pending_scout')}")

# Find the 10 that are different
m1_sites = set(r['site'] for r in rows if 'Scout not submitted' in (r.get('reason_for_decision') or ''))
m3_sites = set(r['site'] for r in needs_survey if 'Scout not submitted' in (r.get('reason_for_decision') or ''))
diff = m1_sites - m3_sites
print(f"\nDifference (in m1 but not m3): {len(diff)} sites")
for r in rows:
    if r.get('site') in diff:
        print(f"  Site {r['site']}: survey_required={r.get('survey_required')} survey_complete={r.get('survey_complete')}")
