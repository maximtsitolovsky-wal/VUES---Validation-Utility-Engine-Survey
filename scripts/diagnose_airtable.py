"""Diagnose Airtable records: check submission IDs, count, and status."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from siteowlqa.airtable_client import AirtableClient
from siteowlqa.config import load_config


def main() -> int:
    cfg = load_config()
    airtable = AirtableClient(cfg)

    records = airtable.list_all_records(max_records=0)
    print(f"Total records in Airtable: {len(records)}\n")

    print("| #  | Record ID           | Submission ID       | Site | Status  |")
    print("|----|--------------------|---------------------|------|---------|")

    for idx, r in enumerate(records, 1):
        rec_id = r.record_id[:18].ljust(18)
        sub_id = (r.submission_id or "<EMPTY>")[:19].ljust(19)
        site = (r.site_number or "?")[:4].ljust(4)
        status = (r.processing_status or "?")[:7].ljust(7)
        print(f"| {idx:<2} | {rec_id} | {sub_id} | {site} | {status} |")

    # Check if submission IDs are populated
    populated = sum(1 for r in records if r.submission_id and r.submission_id.strip() != "")
    empty = len(records) - populated

    print(f"\nSummary:")
    print(f"  Records with Submission ID: {populated}")
    print(f"  Records with empty Submission ID: {empty}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
