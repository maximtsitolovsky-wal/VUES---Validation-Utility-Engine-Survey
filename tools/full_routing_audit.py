"""
Full audit of routing data - verify ALL counts match what the page should show
"""
import json

d = json.load(open('ui/survey_routing_data.json'))
rows = d.get('rows', [])

print("=" * 60)
print("FULL ROUTING DATA AUDIT")
print("=" * 60)
print(f"\nTotal sites: {len(rows)}")

# Simulate getStatus function EXACTLY as routing.html
def get_status(row):
    if row.get('survey_complete') == True:
        return 'survey-completed'
    if row.get('survey_required') == 'NO':
        return 'full-upgrade'
    
    reason = row.get('reason_for_decision', '') or ''
    has_scout = 'No scout submission' not in reason
    
    if not has_scout:
        return 'scout-in-progress'
    
    if row.get('vues_submitted') == True:
        return 'survey-in-progress'
    
    return 'scout-completed'

# === MUTUALLY EXCLUSIVE CATEGORIES (as fixed in routing.html) ===
print("\n" + "=" * 60)
print("TAB CATEGORIES (mutually exclusive)")
print("=" * 60)

# 1. Completed
complete_data = [r for r in rows if r.get('survey_complete') == True]
not_complete = [r for r in rows if r.get('survey_complete') != True]

# 2. No survey needed
no_survey_data = [r for r in not_complete if r.get('survey_required') == 'NO']
needs_survey = [r for r in not_complete if r.get('survey_required') != 'NO']

# 3. Awaiting Scout
scout_data = [r for r in needs_survey if 'No scout submission' in (r.get('reason_for_decision') or '')]
has_scout = [r for r in needs_survey if 'No scout submission' not in (r.get('reason_for_decision') or '')]

# 4. By survey type (from has_scout only)
cctv_data = [r for r in has_scout if r.get('survey_type') == 'CCTV']
fa_data = [r for r in has_scout if r.get('survey_type') == 'FA/INTRUSION']
upgrade_data = [r for r in has_scout if r.get('survey_type') == 'BOTH']
review_data = [r for r in has_scout if r.get('survey_type') in ['REVIEW', 'NONE', None, '']]

print(f"  Completed:       {len(complete_data):>4}")
print(f"  No Survey:       {len(no_survey_data):>4}")
print(f"  Awaiting Scout:  {len(scout_data):>4}")
print(f"  CCTV:            {len(cctv_data):>4}")
print(f"  FA/Intrusion:    {len(fa_data):>4}")
print(f"  Both Surveys:    {len(upgrade_data):>4}")
print(f"  Needs Review:    {len(review_data):>4}")
print(f"  ─────────────────────")
total = len(complete_data) + len(no_survey_data) + len(scout_data) + len(cctv_data) + len(fa_data) + len(upgrade_data) + len(review_data)
print(f"  TOTAL:           {total:>4} {'✓' if total == len(rows) else '✗ MISMATCH!'}")

# === STATUS BAR BREAKDOWN ===
print("\n" + "=" * 60)
print("STATUS BAR (by workflow status)")
print("=" * 60)

from collections import Counter
statuses = Counter(get_status(r) for r in rows)

scout_ip = statuses.get('scout-in-progress', 0)
scout_done = statuses.get('scout-completed', 0)  # "Ready to Assign"
survey_ip = statuses.get('survey-in-progress', 0)
full_upgrade = statuses.get('full-upgrade', 0)
completed = statuses.get('survey-completed', 0)

print(f"  Scout In Progress:  {scout_ip:>4}")
print(f"  Ready to Assign:    {scout_done:>4}  (scout done, needs survey)")
print(f"  Survey In Progress: {survey_ip:>4}")
print(f"  Full Upgrade:       {full_upgrade:>4}")
print(f"  Completed:          {completed:>4}")
print(f"  ─────────────────────")
status_total = scout_ip + scout_done + survey_ip + full_upgrade + completed
print(f"  TOTAL:              {status_total:>4} {'✓' if status_total == len(rows) else '✗ MISMATCH!'}")

# === "DONE" COUNTS PER TAB ===
print("\n" + "=" * 60)
print("DONE COUNTS PER TAB")
print("=" * 60)

cctv_done = len([r for r in cctv_data if get_status(r) == 'survey-completed'])
fa_done = len([r for r in fa_data if get_status(r) == 'survey-completed'])
upgrade_done = len([r for r in upgrade_data if get_status(r) == 'survey-completed'])
review_done = len([r for r in review_data if get_status(r) == 'survey-completed'])

print(f"  CCTV:         {len(cctv_data):>3} total, {cctv_done:>3} done")
print(f"  FA/Intrusion: {len(fa_data):>3} total, {fa_done:>3} done")
print(f"  Both:         {len(upgrade_data):>3} total, {upgrade_done:>3} done")
print(f"  Review:       {len(review_data):>3} total, {review_done:>3} done")

# === VENDOR BREAKDOWN ===
print("\n" + "=" * 60)
print("VENDOR BREAKDOWN")
print("=" * 60)

vendors = Counter(r.get('vendor', 'Unknown') for r in rows)
for vendor, count in vendors.most_common(10):
    print(f"  {vendor}: {count}")

# === CHECK FOR DATA ISSUES ===
print("\n" + "=" * 60)
print("DATA QUALITY CHECKS")
print("=" * 60)

missing_vendor = [r for r in rows if not r.get('vendor')]
missing_type = [r for r in has_scout if not r.get('survey_type') or r.get('survey_type') == 'NONE']
missing_days = [r for r in rows if not r.get('days_to_construction')]

print(f"  Sites missing vendor:        {len(missing_vendor)}")
print(f"  Sites missing survey_type:   {len(missing_type)} (after scout done)")
print(f"  Sites missing days_to_const: {len(missing_days)}")

print("\n" + "=" * 60)
print("AUDIT COMPLETE")
print("=" * 60)
