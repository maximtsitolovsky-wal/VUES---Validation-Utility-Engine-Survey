"""Final verification of routing data."""
import json

print("=" * 60)
print("FINAL ROUTING DATA VERIFICATION")
print("=" * 60)

# Check both files
for path in ['output/survey_routing_data.json', 'ui/survey_routing_data.json']:
    print(f"\n{path}:")
    with open(path) as f:
        d = json.load(f)
    s = d.get('summary', {})
    rows = d.get('rows', [])
    
    print(f"  Total sites: {s.get('total_sites', len(rows))}")
    print(f"  Ready to assign: {s.get('ready_to_assign', 'N/A')}")
    print(f"  Review required: {s.get('review_required', 'N/A')}")
    print(f"  Pending scout: {s.get('pending_scout', 'N/A')}")
    print(f"  Surveys complete: {s.get('surveys_complete', 'N/A')}")
    
    # Row-level check
    by_req = {}
    for r in rows:
        status = r.get('survey_required', 'UNKNOWN')
        by_req[status] = by_req.get(status, 0) + 1
    print(f"  By survey_required: {by_req}")
    
    ready_yes = sum(1 for r in rows if r.get('ready_to_assign') == 'YES')
    print(f"  ready_to_assign=YES: {ready_yes}")

print("\n" + "=" * 60)
print("EXPECTED VALUES:")
print("  Ready to assign: 661")
print("  Review required: 0")  
print("  Pending scout: 107")
print("=" * 60)
