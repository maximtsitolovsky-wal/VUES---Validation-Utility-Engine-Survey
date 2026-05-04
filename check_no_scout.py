"""Check the 107 sites only in Excel (no scout)."""
import sys
sys.path.insert(0, 'src')

import json
from siteowlqa.config import load_config
from siteowlqa.survey_routing import fetch_scout_data, load_schedule_data, DEFAULT_WORKBOOK_PATH

config = load_config()
token = config.scout_airtable_token or config.airtable_token

scout_records = fetch_scout_data(token)
scout_sites = {s.site for s in scout_records}

schedule_records = load_schedule_data(DEFAULT_WORKBOOK_PATH)
schedule_sites = {s.site for s in schedule_records}

only_excel = schedule_sites - scout_sites
print(f"Sites only in Excel (no scout): {len(only_excel)}")
print(f"Sample sites: {sorted(list(only_excel))[:15]}...")

# Now check what status these get in the routing data
with open('output/survey_routing_data.json') as f:
    routing = json.load(f)

rows_by_site = {r['site']: r for r in routing['rows']}

# Check status of sites with no scout
for site in sorted(list(only_excel))[:10]:
    row = rows_by_site.get(site)
    if row:
        print(f"  {site}: survey_required={row['survey_required']}, ready={row['ready_to_assign']}, vendor={row.get('vendor','')}")
