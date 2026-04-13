"""Deep-dive into ERROR status records."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from siteowlqa.airtable_client import AirtableClient
from siteowlqa.config import load_config, ATAIRTABLE_FIELDS as FIELDS


def main() -> int:
    cfg = load_config()
    airtable = AirtableClient(cfg)

    records = airtable.list_all_records(max_records=0)
    error_records = [r for r in records if r.processing_status == "ERROR"]

    print(f"Total ERROR records: {len(error_records)}\n")

    for idx, r in enumerate(error_records, 1):
        print(f"=== ERROR Record #{idx} ===")
        print(f"Record ID        : {r.record_id}")
        print(f"Site Number      : {r.site_number}")
        print(f"Vendor Email     : {r.vendor_email}")
        print(f"Vendor Name      : {r.vendor_name}")
        print(f"Attachment       : {r.attachment_filename}")
        print(f"Submitted At     : {r.submitted_at}")
        print(f"Status           : {r.processing_status}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
