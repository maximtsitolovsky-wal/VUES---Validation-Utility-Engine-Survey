"""Quick check record fields."""
import sys
sys.path.insert(0, 'src')
from siteowlqa.config import load_config
from siteowlqa.airtable_client import AirtableClient

cfg = load_config()
at = AirtableClient(cfg)
f = at.get_record_fields('rec4K3ukMKat6CBE0')

print('ALL FIELDS for rec4K3ukMKat6CBE0:')
for k, v in sorted(f.items()):
    val_str = str(v)[:100] if v else 'EMPTY'
    print(f'  {k}: {val_str}')
