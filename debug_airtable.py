"""Debug script to check Airtable field names."""
import requests
import sys
sys.path.insert(0, "src")

from siteowlqa.config import load_config

cfg = load_config()
token = cfg.scout_airtable_token or cfg.airtable_token
base_id = "appAwgaX89x0JxG3Z"
table_id = "tblC4o9AvVulyxFMk"

url = f"https://api.airtable.com/v0/{base_id}/{table_id}"
headers = {"Authorization": f"Bearer {token}"}

print(f"Fetching from: {url}")
resp = requests.get(url, headers=headers, params={"maxRecords": 1}, timeout=30)
print(f"Status: {resp.status_code}")

data = resp.json()

if "records" in data and data["records"]:
    fields = data["records"][0].get("fields", {})
    print(f"\nFound {len(fields)} fields in first record:")
    for k in sorted(fields.keys()):
        v = fields[k]
        preview = str(v)[:60] if v else "(empty)"
        print(f"  {k}: {preview}")
else:
    print("No records or error:", data)
