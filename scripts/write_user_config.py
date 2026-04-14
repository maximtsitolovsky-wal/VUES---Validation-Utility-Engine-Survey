import json
import sys
from pathlib import Path

config_dir = Path.home() / '.siteowlqa'
config_dir.mkdir(parents=True, exist_ok=True)
config_path = config_dir / 'config.json'

# Values from the existing .env file
data = {
    'sql_server':                        'localhost\\SITEOWL',
    'sql_database':                      'SiteOwlQA',
    'sql_driver':                        'ODBC Driver 17 for SQL Server',
    'airtable_token':                    'YOUR_AIRTABLE_TOKEN_HERE',
    'airtable_base_id':                  'apptK6zNN0Hf3OuoJ',
    'airtable_table_name':               'Submissions',
    'element_llm_gateway_url':           '',
    'element_llm_gateway_api_key':       '',
    'element_llm_gateway_model':         'element:gpt-4o',
    'element_llm_gateway_project_id':    '',
    'wmt_ca_path':                       '',
    'reference_workbook_path':           r'C:\Users\vn59j7j\OneDrive - Walmart Inc\SQL DB MASTER.xlsx',
    'reference_workbook_sheet':          'SQL DB MASTER',
    'reference_workbook_site_id_column': 'SelectedSiteID',
}

config_path.write_text(json.dumps(data, indent=2), encoding='utf-8')

result_lines = [
    f'OK: Config written to {config_path}',
    f'OK: File size = {config_path.stat().st_size} bytes',
]

with open('scripts/_setup_result.txt', 'w') as f:
    f.write('\n'.join(result_lines) + '\n')

print('\n'.join(result_lines))
sys.stdout.flush()
