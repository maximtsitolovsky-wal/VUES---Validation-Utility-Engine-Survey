"""
One-shot diagnostic: prints every field name returned by the Scout Airtable
for the first 3 records, so we can confirm column names before the downloader
runs.  Safe to delete after confirming field names.
"""
import sys
import requests

API_KEY  = "patPR0WWxXCE0loRO.d18126548ad25b8aaf9fd43e2ac69479b1378e46d7f8c6efbdd88f7197a4d495"
BASE_ID  = "appAwgaX89x0JxG3Z"
TABLE_ID = "tblC4o9AvVulyxFMk"
HEADERS  = {"Authorization": f"Bearer {API_KEY}"}


def main() -> int:
    resp = requests.get(
        f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}",
        headers=HEADERS,
        params={"maxRecords": 5},
        timeout=20,
    )
    print(f"HTTP {resp.status_code}")
    if resp.status_code != 200:
        print(resp.text)
        return 1

    records = resp.json().get("records", [])
    print(f"Records returned: {len(records)}\n")

    seen_attach_fields: dict[str, int] = {}

    for i, rec in enumerate(records, 1):
        fields = rec.get("fields", {})
        print(f"--- Record {i}  id={rec['id']} ---")
        for k, v in fields.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                keys = list(v[0].keys())
                print(f"  ATTACHMENT  [{k!r}]  count={len(v)}  att-keys={keys}")
                seen_attach_fields[k] = seen_attach_fields.get(k, 0) + len(v)
            else:
                print(f"  FIELD       [{k!r}]  = {str(v)[:100]}")
        print()

    print("=== ATTACHMENT FIELD SUMMARY ===")
    if seen_attach_fields:
        for name, total in seen_attach_fields.items():
            print(f"  {name!r}  →  {total} attachment(s) across sample records")
    else:
        print("  *** NO attachment-type fields found in these records ***")
        print("  Either the field name differs or records have no images uploaded.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
