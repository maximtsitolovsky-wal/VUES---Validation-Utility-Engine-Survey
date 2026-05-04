"""Check source data for routing."""
import sys
sys.path.insert(0, 'src')

from siteowlqa.config import load_config
from siteowlqa.survey_routing import fetch_scout_data, load_schedule_data, DEFAULT_WORKBOOK_PATH

config = load_config()
token = config.scout_airtable_token or config.airtable_token

print("Fetching scout data from Airtable...")
scout_records = fetch_scout_data(token)
scout_sites = {s.site for s in scout_records}
print(f"Scout sites from Airtable: {len(scout_sites)}")

print("\nLoading schedule data from Excel...")
schedule_records = load_schedule_data(DEFAULT_WORKBOOK_PATH)
schedule_sites = {s.site for s in schedule_records}
print(f"Schedule sites from Excel: {len(schedule_sites)}")

# Union
all_sites = scout_sites | schedule_sites
print(f"\nUnion (all sites): {len(all_sites)}")

# Intersection 
common = scout_sites & schedule_sites
print(f"Intersection (in both): {len(common)}")

# Only in scout
only_scout = scout_sites - schedule_sites
print(f"Only in Scout (no Excel entry): {len(only_scout)}")
if only_scout and len(only_scout) < 20:
    print(f"  Sites: {sorted(only_scout)[:10]}...")

# Only in Excel
only_excel = schedule_sites - scout_sites
print(f"Only in Excel (no scout yet): {len(only_excel)}")
if only_excel and len(only_excel) < 20:
    print(f"  Sites: {sorted(only_excel)[:10]}...")
