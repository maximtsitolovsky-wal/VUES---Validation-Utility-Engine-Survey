"""Refresh survey routing with correct tokens."""
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

print("Starting...")
sys.stdout.flush()

from pathlib import Path
from siteowlqa.config import load_config
from siteowlqa.survey_routing import refresh_survey_routing

cfg = load_config()
scout_token = cfg.scout_airtable_token or cfg.airtable_token
survey_token = cfg.airtable_token

print(f"Scout token: {scout_token[:15]}...")
print(f"Survey token: {survey_token[:15]}...")
sys.stdout.flush()

refresh_survey_routing(
    scout_token=scout_token,
    survey_token=survey_token,
    output_dir=Path('output'),
    sync_to_airtable=False
)

import shutil
shutil.copy('output/survey_routing_data.json', 'ui/survey_routing_data.json')
print("Done!")
