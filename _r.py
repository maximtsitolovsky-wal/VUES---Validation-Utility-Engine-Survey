"""Refresh team dashboard data."""
import logging
import shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from siteowlqa.config import load_config
from siteowlqa.airtable_client import AirtableClient
from siteowlqa.team_dashboard_data import refresh_team_dashboard_data

cfg = load_config()
airtable = AirtableClient(cfg)

print("Refreshing team dashboard data...")
refresh_team_dashboard_data(airtable=airtable, cfg=cfg, output_dir=Path('output'))

print("Copying to ui/...")
shutil.copy('output/team_dashboard_data.json', 'ui/team_dashboard_data.json')
shutil.copy('output/survey_routing_data.json', 'ui/survey_routing_data.json')
print("Done!")
