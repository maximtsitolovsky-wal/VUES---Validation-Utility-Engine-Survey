import requests
import json
from pathlib import Path

cfg = json.load(open(Path.home() / '.siteowlqa' / 'config.json'))
token = cfg.get('scout_airtable_token')

url = 'https://api.airtable.com/v0/appAwgaX89x0JxG3Z/tblC4o9AvVulyxFMk'
headers = {'Authorization': f'Bearer {token}'}
params = {'view': 'viwYF5nUCDkVFDNT8', 'pageSize': 100}

total = 0
while True:
    r = requests.get(url, headers=headers, params=params, timeout=30)
    data = r.json()
    if 'error' in data:
        print(f'Error: {data}')
        break
    count = len(data.get('records', []))
    total += count
    print(f'Page: {count} (total: {total})')
    offset = data.get('offset')
    if not offset:
        break
    params['offset'] = offset

print(f'\n=== TOTAL RECORDS IN VIEW: {total} ===')
