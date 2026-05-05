from pathlib import Path
from siteowlqa.config import load_config
from siteowlqa.survey_routing import refresh_survey_routing
import shutil
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

cfg = load_config()
refresh_survey_routing(
    scout_token=cfg.scout_airtable_token or cfg.airtable_token,
    survey_token=cfg.airtable_token,
    output_dir=Path('output'),
    sync_to_airtable=False
)
shutil.copy('output/survey_routing_data.json', 'ui/survey_routing_data.json')
print('Done!')
