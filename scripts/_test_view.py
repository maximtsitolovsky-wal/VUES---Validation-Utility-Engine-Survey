import json
from pathlib import Path
import requests

cfg = json.load(open(Path.home() / '.siteowlqa' / 'config.json'))
token = cfg.get('scout_airtable_token')
base_id = cfg.get('scout_airtable_base_id')
table = cfg.get('scout_airtable_table_name')
view_id = cfg.get('scout_airtable_view_id')

print(f'View ID from config: {view_id}')

url = f'https://api.airtable.com/v0/{base_id}/{table}'
headers = {'Authorization': f'Bearer {token}'}
params = {'view': view_id, 'pageSize': 100}

r = requests.get(url, headers=headers, params=params, timeout=30)
data = r.json()
print(f'Records from view: {len(data.get("records", []))}')
if 'error' in data:
    print(f'Error: {data}')
