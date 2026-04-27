"""Debug: Check if view_id is being used correctly."""
import sys
sys.path.insert(0, 'src')

from siteowlqa.config import load_config, reset_config_singleton
from siteowlqa.user_config import load_user_config

# Reset any cached config
reset_config_singleton()

# Load fresh
user_cfg = load_user_config()
print(f"User config scout_airtable_view_id: {repr(user_cfg.scout_airtable_view_id)}")

cfg = load_config()
print(f"AppConfig scout_airtable_view_id: {repr(cfg.scout_airtable_view_id)}")

# Now test the API call directly with the view
import requests
url = f'https://api.airtable.com/v0/{cfg.scout_airtable_base_id}/{cfg.scout_airtable_table_name}'
headers = {'Authorization': f'Bearer {cfg.scout_airtable_token}'}
params = {'pageSize': 100}

if cfg.scout_airtable_view_id:
    params['view'] = cfg.scout_airtable_view_id
    print(f"Using view: {cfg.scout_airtable_view_id}")
else:
    print("NO VIEW SET - querying all records!")

r = requests.get(url, headers=headers, params=params, timeout=30)
data = r.json()
if 'error' in data:
    print(f"API Error: {data}")
else:
    print(f"First page records: {len(data.get('records', []))}")
