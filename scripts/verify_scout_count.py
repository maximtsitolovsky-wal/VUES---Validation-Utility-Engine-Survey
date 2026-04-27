#!/usr/bin/env python3
"""Verify Scout submission count directly from Airtable."""

import json
from pathlib import Path
import requests

def main():
    # Load user config
    config_path = Path.home() / '.siteowlqa' / 'config.json'
    if not config_path.exists():
        print('ERROR: No config file found at', config_path)
        return
    
    cfg = json.load(open(config_path))
    token = cfg.get('scout_airtable_token') or cfg.get('airtable_token')
    base_id = cfg.get('scout_airtable_base_id')
    table = cfg.get('scout_airtable_table_name')
    view_id = cfg.get('scout_airtable_view_id', '')
    
    print(f'Base ID: {base_id}')
    print(f'Table: {table}')
    print(f'View: {view_id or "(none - querying all records)"}')
    print()
    
    if not token or not base_id or not table:
        print('ERROR: Missing scout config (token/base_id/table)')
        return
    
    url = f'https://api.airtable.com/v0/{base_id}/{requests.utils.quote(table, safe="")}'
    headers = {'Authorization': f'Bearer {token}'}
    params = {'pageSize': 100}
    if view_id:
        params['view'] = view_id
    
    total = 0
    pages = 0
    while True:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        if r.status_code != 200:
            print(f'ERROR: Airtable returned {r.status_code}')
            print(r.text[:500])
            return
        data = r.json()
        count = len(data.get('records', []))
        total += count
        pages += 1
        print(f'Page {pages}: {count} records (running total: {total})')
        offset = data.get('offset')
        if not offset:
            break
        params['offset'] = offset
    
    print()
    print('=' * 50)
    print(f'  AIRTABLE SCOUT TOTAL: {total} records')
    print('=' * 50)
    
    # Compare with cached data
    cached_path = Path('output/team_dashboard_data.json')
    if cached_path.exists():
        cached = json.load(open(cached_path))
        cached_count = len(cached.get('scout', {}).get('records', []))
        print(f'  CACHED (dashboard): {cached_count} records')
        if cached_count == total:
            print('  ✓ MATCH!')
        else:
            print(f'  ✗ MISMATCH: difference of {abs(total - cached_count)}')
    print()

if __name__ == '__main__':
    main()
