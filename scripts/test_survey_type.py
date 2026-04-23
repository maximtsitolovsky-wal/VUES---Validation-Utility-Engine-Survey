"""Quick test of survey type grading."""
import sys
sys.path.insert(0, 'src')

from siteowlqa.config import load_config, get_grade_columns_for_survey_type
from siteowlqa.airtable_client import AirtableClient

print("=== Survey Type Grading Test ===\n")

# Test config
print("Grading columns by type:")
for stype in ['CCTV', 'FA/Intrusion', 'BOTH']:
    cols = get_grade_columns_for_survey_type(stype)
    print(f"  {stype}: {len(cols)} columns")

print()

# Test Airtable fetch
try:
    cfg = load_config()
    client = AirtableClient(cfg)
    records = client.list_all_records(max_records=5)
    print(f"Fetched {len(records)} records from Airtable:\n")
    for r in records:
        st = r.survey_type or "(not set)"
        print(f"  Site {r.site_number}: Survey Type = {st}")
except Exception as e:
    print(f"Error: {e}")
