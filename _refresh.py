"""Quick refresh of survey routing data."""
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
print("Starting...")
sys.stdout.flush()

from pathlib import Path
from siteowlqa.config import load_config
from siteowlqa.survey_routing import refresh_survey_routing

cfg = load_config()
print(f"Token: {cfg.airtable_token[:15]}...")

print("Refreshing routing data...")
refresh_survey_routing(
    token=cfg.airtable_token,
    output_dir=Path('output'),
    sync_to_airtable=False
)

print("Copying to ui/...")
import shutil
shutil.copy('output/survey_routing_data.json', 'ui/survey_routing_data.json')
print("Done!")
