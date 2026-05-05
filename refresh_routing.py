"""Quick script to refresh survey routing data."""
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
log = logging.getLogger(__name__)

print("Starting survey refresh...")
sys.stdout.flush()

from pathlib import Path
from siteowlqa.config import load_config
from siteowlqa.survey_routing import fetch_survey_submissions, refresh_survey_routing

print("Loading config...")
cfg = load_config()
print(f"Token loaded: {cfg.airtable_token[:15]}...")

print("Fetching survey submissions from Airtable...")
completed = fetch_survey_submissions(cfg.airtable_token)
print(f"Found {len(completed)} completed survey sites in Airtable")
if completed:
    print(f"Sample sites: {list(completed)[:10]}")

print("\nRefreshing full routing data...")
refresh_survey_routing(
    token=cfg.airtable_token,
    output_dir=Path('output'),
    sync_to_airtable=False
)

print("\nCopying to ui/...")
import shutil
shutil.copy('output/survey_routing_data.json', 'ui/survey_routing_data.json')

print("Done!")
