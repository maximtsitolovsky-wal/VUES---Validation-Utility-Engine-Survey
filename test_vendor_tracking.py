"""Quick test for vendor assignment tracking"""
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')

from siteowlqa.config import load_config
from siteowlqa.airtable_client import AirtableClient  
from siteowlqa.team_dashboard_data import refresh_team_dashboard_data

cfg = load_config()
airtable = AirtableClient(cfg)
output_dir = Path("output")

print("\n=== Testing vendor assignment tracking ===\n")
refresh_team_dashboard_data(airtable=airtable, cfg=cfg, output_dir=output_dir)

print("\n=== Checking output ===\n")
import json
data = json.loads((output_dir / "team_dashboard_data.json").read_text())
print(f"Keys in output: {list(data.keys())}")

if "vendor_assignments" in data:
    print("\nVendor assignments found!")
    print(f"  Configured: {data['vendor_assignments'].get('configured')}")
    print(f"  Vendors: {len(data['vendor_assignments'].get('vendors', []))}")
    for v in data['vendor_assignments'].get('vendors', []):
        print(f"    - {v['vendor_name']}: {v['remaining']} remaining, {v['completed']} done")
else:
    print("\nVendor assignments NOT found!")
