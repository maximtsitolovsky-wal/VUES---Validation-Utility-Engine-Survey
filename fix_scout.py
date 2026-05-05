import json

with open('ui/survey_routing_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Sites that need scout_submitted = True (not awaiting scout)
fix_scout = ['2070', '2071', '2188', '2308', '3883']

# CEI sites pending scout - user said 3 need to go to BOTH surveys
cei_pending = []

for row in data['rows']:
    site_id = str(row.get('site'))
    
    # Fix the 5 known sites - mark scout as done
    if site_id in fix_scout:
        row['scout_submitted'] = True
        row['schedule_status'] = 'COMPLETE'
        row['survey_type'] = 'BOTH'
        row['survey_required'] = 'YES'
        print(f"Fixed {site_id} ({row['vendor']}): scout_submitted=True, survey_type=BOTH")
    
    # Track CEI sites still pending scout
    if row.get('vendor') == 'CEI' and not row.get('scout_submitted'):
        cei_pending.append(site_id)

print(f"\nCEI sites still pending scout: {cei_pending}")
print("Which 3 of these should be marked as BOTH surveys under CEI?")

with open('ui/survey_routing_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print("\nSaved! (5 sites fixed)")
