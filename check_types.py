import json

d = json.load(open('output/survey_routing_data.json'))

print("Survey Type Distribution:")
types = {}
for r in d['rows']:
    t = r['survey_type']
    types[t] = types.get(t, 0) + 1
for t, c in sorted(types.items(), key=lambda x: -x[1]):
    print(f"  {t}: {c}")

print("\nSample BOTH site:")
both_sites = [r for r in d['rows'] if r['survey_type'] == 'BOTH']
if both_sites:
    r = both_sites[0]
    print(f"  Site: {r['site']}")
    print(f"  Flags: {r['supplemental_flags']}")

print("\nLooking for CCTV-only or FA-only sites...")
cctv_only = [r for r in d['rows'] if r['survey_type'] == 'CCTV']
fa_only = [r for r in d['rows'] if r['survey_type'] == 'FA/INTRUSION']
print(f"  CCTV-only sites: {len(cctv_only)}")
print(f"  FA/INTRUSION-only sites: {len(fa_only)}")
