import sys
sys.path.insert(0, 'src')
import json
from pathlib import Path

from siteowlqa.team_dashboard_data import refresh_team_dashboard_data
from siteowlqa.airtable_client import AirtableClient
from siteowlqa.config import load_config

# Load config
cfg = load_config()

# Initialize Airtable client
airtable = AirtableClient(cfg=cfg)

# Refresh data
print("Refreshing team dashboard data...")
refresh_team_dashboard_data(airtable=airtable, cfg=cfg, output_dir=Path('output'))

# Verify
print("\n=== VENDOR ASSIGNMENTS ===")
with open('output/team_dashboard_data.json') as f:
    data = json.load(f)
    
for v in data.get('vendor_assignments', {}).get('vendors', []):
    print(f"{v['vendor_name']}: {v['completed']}/{v['total_assigned']}")
