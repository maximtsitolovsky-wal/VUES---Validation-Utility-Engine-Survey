import json

with open('ui/survey_routing_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Count sites with 'Scout not submitted' in reason
scout_not_submitted = [r for r in data['rows'] if 'Scout not submitted' in (r.get('reason_for_decision') or '')]
print(f"Actual sites with 'Scout not submitted': {len(scout_not_submitted)}")
print(f"Summary pending_scout (stale): {data['summary']['pending_scout']}")

# Update summary
data['summary']['pending_scout'] = len(scout_not_submitted)
data['summary']['pending_type'] = len(scout_not_submitted)

with open('ui/survey_routing_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print(f"Updated pending_scout to: {len(scout_not_submitted)}")
