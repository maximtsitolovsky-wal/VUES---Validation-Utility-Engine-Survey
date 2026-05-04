"""Final state check."""
import json
import sys
sys.path.insert(0, 'src')

from siteowlqa.config import load_config
from siteowlqa.survey_routing import fetch_scout_data, DEFAULT_WORKBOOK_PATH

config = load_config()
token = config.scout_airtable_token or config.airtable_token

# Scout sites from Airtable (source of truth)
scout_records = fetch_scout_data(token)
scout_sites = {s.site for s in scout_records}
print(f"Scout sites from Airtable: {len(scout_sites)}")

# Load routing data
with open('output/survey_routing_data.json') as f:
    routing = json.load(f)
rows = routing['rows']

print(f"Total routing rows: {len(rows)}")

# For the 661 scout sites, what's their status?
print("\n=== STATUS OF 661 SCOUT SITES ===")
scout_rows = [r for r in rows if r['site'] in scout_sites]
print(f"Routing rows for scout sites: {len(scout_rows)}")

# By survey_required
by_req = {}
for r in scout_rows:
    s = r.get('survey_required', 'UNKNOWN')
    by_req[s] = by_req.get(s, 0) + 1
print(f"By survey_required: {by_req}")

# By ready_to_assign
ready_yes = sum(1 for r in scout_rows if r.get('ready_to_assign') == 'YES')
ready_no = sum(1 for r in scout_rows if r.get('ready_to_assign') == 'NO')
print(f"Ready=YES: {ready_yes}, Ready=NO: {ready_no}")

# By survey_complete
complete = sum(1 for r in scout_rows if r.get('survey_complete'))
print(f"Survey complete: {complete}")

# Sites needing survey but not complete
need_survey = [r for r in scout_rows if r.get('survey_required') == 'YES' and not r.get('survey_complete')]
print(f"Sites needing survey (not complete): {len(need_survey)}")

print("\n=== 107 SITES WITHOUT SCOUT ===")
no_scout = [r for r in rows if r['site'] not in scout_sites]
print(f"Sites without scout data: {len(no_scout)}")
by_req2 = {}
for r in no_scout:
    s = r.get('survey_required', 'UNKNOWN')
    by_req2[s] = by_req2.get(s, 0) + 1
print(f"By survey_required: {by_req2}")
