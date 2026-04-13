"""Debug: Show ALL records fetched before regrade loop."""

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
    print(f"Total records returned by list_all_records(): {len(records)}")
    print()

    for idx, r in enumerate(records, 1):
        print(f"{idx:2}. {r.record_id} | site={r.site_number:5} | status={r.processing_status:7} | attachment={r.attachment_filename}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
