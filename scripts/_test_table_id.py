import requests
import json
from pathlib import Path

cfg = json.load(open(Path.home() / '.siteowlqa' / 'config.json'))
token = cfg.get('scout_airtable_token')

# Use table ID from URL instead of name
url = 'https://api.airtable.com/v0/appAwgaX89x0JxG3Z/tblC4o9AvVulyxFMk'
headers = {'Authorization': f'Bearer {token}'}
params = {'view': 'viwYF5nUCDkVFDNT8', 'pageSize': 100}

print(f"Querying: {url}")
print(f"View: {params['view']}")

r = requests.get(url, headers=headers, params=params, timeout=30)
data = r.json()
if 'error' in data:
    print(f'Error: {data}')
else:
    count = len(data.get('records', []))
    print(f'Records: {count}')
    
    # Check for more pages
    if data.get('offset'):
        print('(more pages exist)')
