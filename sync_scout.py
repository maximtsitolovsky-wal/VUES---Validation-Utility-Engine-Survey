import json

with open('ui/survey_routing_data.json', 'r') as f:
    data = json.load(f)

# Count actual awaiting scout
awaiting = [r for r in data['rows'] if 'Scout not submitted' in (r.get('reason_for_decision') or '')]
print(f"Actual Awaiting Scout (from rows): {len(awaiting)}")
print(f"Summary pending_scout field: {data['summary'].get('pending_scout', 'N/A')}")

# Update summary to match
data['summary']['pending_scout'] = len(awaiting)
data['summary']['pending_type'] = len(awaiting)

with open('ui/survey_routing_data.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f"\nUpdated summary pending_scout to: {len(awaiting)}")
