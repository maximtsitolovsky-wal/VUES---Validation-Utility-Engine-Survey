#!/usr/bin/env python3
"""Check scout data in team_dashboard_data.json."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json

print("Loading team_dashboard_data.json...")
with open('ui/team_dashboard_data.json') as f:
    data = json.load(f)

print(f"Top-level keys: {list(data.keys())}")

scout = data.get('scout', {})
if not scout:
    print("No 'scout' key found!")
else:
    print(f"Scout keys: {list(scout.keys())[:15]}")
    
    # Check various possible structures
    for key in ['completed', 'total', 'unique_sites', 'count', 'records', 'sites', 'submissions']:
        if key in scout:
            val = scout[key]
            if isinstance(val, (int, float, str)):
                print(f"  {key}: {val}")
            elif isinstance(val, list):
                print(f"  {key}: {len(val)} items")
            elif isinstance(val, dict):
                print(f"  {key}: dict with {len(val)} keys")
