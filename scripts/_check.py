import sys
sys.path.insert(0, 'src')
from siteowlqa.config import load_config
from siteowlqa.airtable_client import AirtableClient
cfg = load_config()
at = AirtableClient(cfg)
f = at.get_record_fields('recryYpfpuVlYKm1g')
print('Status:', f.get('Processing Status'))
print('Score:', f.get('Score'))
print('Fail Summary:', f.get('Fail Summary', 'N/A')[:500])
