import json

with open('ui/survey_routing_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Count sites with 'Scout not submitted' in reason
scout_not_submitted = [r for r in data['rows'] if 'Scout not submitted' in (r.get('reason_for_decision') or '')]
print(f"Actual sites with 'Scout not submitted': {len(scout_not_submitted)}")

# Show first 5 and our fixed sites
print('\nFirst 5 sites still awaiting scout:')
for r in scout_not_submitted[:5]:
    print(f"  {r.get('site')}: {r.get('reason_for_decision')[:50]}")

# Check our 10 sites
our_sites = ['9','864','1590','2646','3072','2070','2071','2188','2308','3883']
print('\nOur 10 sites:')
for r in data['rows']:
    if str(r.get('site')) in our_sites:
        has_scout_text = 'Scout not submitted' in (r.get('reason_for_decision') or '')
        print(f"  {r.get('site')}: has_scout_not_submitted={has_scout_text}  reason={r.get('reason_for_decision')[:40]}...")
print(f"Summary pending_scout (stale): {data['summary']['pending_scout']}")

# Update summary
data['summary']['pending_scout'] = len(scout_not_submitted)
data['summary']['pending_type'] = len(scout_not_submitted)

with open('ui/survey_routing_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print(f"Updated pending_scout to: {len(scout_not_submitted)}")
