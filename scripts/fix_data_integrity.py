#!/usr/bin/env python
"""
Comprehensive data integrity fix for VUES.
Regenerates all dashboard data with correct vendor assignments.

Fixes:
1. vendor_locations.json - merge Techwise/SAS into CEI
2. survey_routing_data.json - ensure fresh data
3. Sync ui/ and output/ directories
"""
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, 'src')

print("=" * 70)
print("VUES DATA INTEGRITY FIX")
print(f"Timestamp: {datetime.now().isoformat()}")
print("=" * 70)

# === 1. FIX vendor_locations.json ===
print("\n[1/4] Fixing vendor_locations.json...")

vendor_locations_path = Path('ui/vendor_locations.json')
with open(vendor_locations_path) as f:
    loc_data = json.load(f)

# Vendor reassignment mapping
REASSIGN = {'Techwise': 'CEI', 'SAS': 'CEI'}
CEI_COLOR = "#2ed7ff"

# Fix markers
new_markers = []
cei_additions = {}  # state -> count to add to CEI

for marker in loc_data['markers']:
    old_vendor = marker['vendor']
    if old_vendor in REASSIGN:
        new_vendor = REASSIGN[old_vendor]
        state = marker['state']
        count = marker['count']
        
        # Track what we're merging
        key = f"{state}-{new_vendor}"
        if key not in cei_additions:
            cei_additions[key] = {'state': state, 'count': 0, 'location': marker['location']}
        cei_additions[key]['count'] += count
        
        print(f"  Merging {old_vendor} {state} ({count}) -> {new_vendor}")
    else:
        new_markers.append(marker)

# Find existing CEI markers and add to them, or create new ones
for key, data in cei_additions.items():
    state = data['state']
    existing = None
    for m in new_markers:
        if m['vendor'] == 'CEI' and m['state'] == state:
            existing = m
            break
    
    if existing:
        existing['count'] += data['count']
        print(f"  Added {data['count']} to existing CEI-{state} (now {existing['count']})")
    else:
        # Create new CEI marker for this state
        new_marker = {
            'id': f"{state}-CEI",
            'vendor': 'CEI',
            'state': state,
            'location': data['location'],
            'count': data['count'],
            'color': CEI_COLOR
        }
        new_markers.append(new_marker)
        print(f"  Created new CEI-{state} with {data['count']} sites")

loc_data['markers'] = new_markers

# Fix state_totals
new_state_totals = {}
for state, vendors in loc_data['state_totals'].items():
    new_vendors = {}
    for vendor, count in vendors.items():
        if vendor in REASSIGN:
            target = REASSIGN[vendor]
            new_vendors[target] = new_vendors.get(target, 0) + count
        else:
            new_vendors[vendor] = new_vendors.get(vendor, 0) + count
    new_state_totals[state] = new_vendors

loc_data['state_totals'] = new_state_totals

# Fix vendor_totals
old_totals = loc_data['vendor_totals']
new_totals = {}
for vendor, count in old_totals.items():
    if vendor in REASSIGN:
        target = REASSIGN[vendor]
        new_totals[target] = new_totals.get(target, 0) + count
    else:
        new_totals[vendor] = new_totals.get(vendor, 0) + count

# Remove Techwise and SAS if they still exist
new_totals.pop('Techwise', None)
new_totals.pop('SAS', None)

loc_data['vendor_totals'] = new_totals

print(f"\n  Old vendor_totals: {old_totals}")
print(f"  New vendor_totals: {new_totals}")

# Save
with open(vendor_locations_path, 'w') as f:
    json.dump(loc_data, f, indent=2)
print(f"  Saved: {vendor_locations_path}")

# Also save to output/
output_loc_path = Path('output/vendor_locations.json')
with open(output_loc_path, 'w') as f:
    json.dump(loc_data, f, indent=2)
print(f"  Saved: {output_loc_path}")

# === 2. REGENERATE survey_routing_data.json ===
print("\n[2/4] Regenerating survey_routing_data.json...")

from siteowlqa.config import load_config
from siteowlqa.survey_routing import build_survey_routing_data, DEFAULT_WORKBOOK_PATH

cfg = load_config()
token = cfg.scout_airtable_token or cfg.airtable_token

routing_data = build_survey_routing_data(token, DEFAULT_WORKBOOK_PATH)

# Save to ui/
ui_routing_path = Path('ui/survey_routing_data.json')
with open(ui_routing_path, 'w') as f:
    json.dump(routing_data, f, indent=2)
print(f"  Saved: {ui_routing_path}")

# Save to output/
output_routing_path = Path('output/survey_routing_data.json')
with open(output_routing_path, 'w') as f:
    json.dump(routing_data, f, indent=2)
print(f"  Saved: {output_routing_path}")

# Print summary
s = routing_data['summary']
print(f"\n  Total sites: {s['total_sites']}")
print(f"  Surveys required: {s['surveys_required']}")
print(f"  Pending scout: {s['pending_scout']}")
print(f"  Ready to assign: {s['ready_to_assign']}")

# === 3. SYNC routing.html ===
print("\n[3/4] Syncing routing.html...")
import shutil
shutil.copy('ui/routing.html', 'output/routing.html')
print("  Copied ui/routing.html -> output/routing.html")

# === 4. VERIFY DATA INTEGRITY ===
print("\n[4/4] Verifying data integrity...")

# Check vendor_locations
with open(vendor_locations_path) as f:
    verified_loc = json.load(f)

techwise_found = any(m['vendor'] == 'Techwise' for m in verified_loc['markers'])
sas_found = any(m['vendor'] == 'SAS' for m in verified_loc['markers'])

print(f"  Techwise in markers: {'FAIL - STILL PRESENT' if techwise_found else 'OK - Removed'}")
print(f"  SAS in markers: {'FAIL - STILL PRESENT' if sas_found else 'OK - Removed'}")
print(f"  vendor_totals keys: {list(verified_loc['vendor_totals'].keys())}")

# Check survey_routing_data
with open(ui_routing_path) as f:
    verified_routing = json.load(f)

print(f"  survey_routing_data generated_at: {verified_routing.get('generated_at', 'MISSING')}")

# Final vendor breakdown
print("\n" + "=" * 70)
print("FINAL VENDOR BREAKDOWN")
print("=" * 70)
print(f"\nvendor_locations.json totals:")
for v, c in sorted(verified_loc['vendor_totals'].items()):
    print(f"  {v}: {c}")

print(f"\nsurvey_routing_data.json breakdown:")
rows = verified_routing.get('rows', [])
vendor_counts = {}
for r in rows:
    v = r.get('vendor') or 'unassigned'
    vendor_counts[v] = vendor_counts.get(v, 0) + 1

for v, c in sorted(vendor_counts.items()):
    print(f"  {v}: {c}")

print("\n" + "=" * 70)
print("DATA INTEGRITY FIX COMPLETE")
print("=" * 70)
