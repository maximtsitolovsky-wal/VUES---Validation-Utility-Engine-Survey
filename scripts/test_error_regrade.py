"""Manually regrade the 2 ERROR records to debug."""

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
    error_records = [r for r in records if r.processing_status == "ERROR"]

    print(f"Found {len(error_records)} ERROR records\n")

    # Try to actually process them through the regrade_one function
    # Import it here to avoid circular imports
    import regrade_all_airtable_submissions as regrade_module

    for r in error_records:
        print(f"\nRegrading: {r.record_id}")
        try:
            result = regrade_module.regrade_one(cfg, airtable, r)
            print(f"  Result: {result.new_status} | score={result.new_score}")
            if result.note:
                print(f"  Note: {result.note}")
        except Exception as e:
            print(f"  Exception: {type(e).__name__}: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
