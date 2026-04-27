import sys
sys.path.insert(0, 'src')
from siteowlqa.config import AppConfig
cfg = AppConfig()
print('scout_airtable_view_id:', repr(cfg.scout_airtable_view_id))
print('scout_airtable_base_id:', repr(cfg.scout_airtable_base_id))
print('scout_airtable_table_name:', repr(cfg.scout_airtable_table_name))
