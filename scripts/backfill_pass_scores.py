"""backfill_pass_scores.py -- One-shot: find all PASS records with blank Score
and write 'PASS' to the Score field in Airtable.
"""
import requests
from siteowlqa.config import load_config, ATAIRTABLE_FIELDS as FIELDS

cfg = load_config()
base_url = f"https://api.airtable.com/v0/{cfg.airtable_base_id}/{cfg.airtable_table_name}"
headers = {
    "Authorization": f"Bearer {cfg.airtable_token}",
    "Content-Type":  "application/json",
}

# Fetch all records where Processing Status = PASS
params = {
    "filterByFormula": f"{{{FIELDS.status}}} = 'PASS'",
    "fields[]": [FIELDS.status, FIELDS.score],
}

print("Fetching PASS records from Airtable...")
all_records = []
offset = None
while True:
    if offset:
        params["offset"] = offset
    r = requests.get(base_url, headers=headers, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    all_records.extend(data.get("records", []))
    offset = data.get("offset")
    if not offset:
        break

print(f"Found {len(all_records)} PASS record(s) total.")

# Filter to ones where Score is blank
needs_fix = [
    rec for rec in all_records
    if not rec.get("fields", {}).get(FIELDS.score)
]
print(f"{len(needs_fix)} have a blank Score field -- patching now...")

for rec in needs_fix:
    rid = rec["id"]
    r = requests.patch(
        f"{base_url}/{rid}",
        headers=headers,
        json={"fields": {FIELDS.score: "PASS"}},
        timeout=15,
    )
    if r.ok:
        print(f"  [OK] {rid} -> Score = 'PASS'")
    else:
        print(f"  [!!] {rid} -> {r.status_code}: {r.text[:200]}")

print("Done.")
