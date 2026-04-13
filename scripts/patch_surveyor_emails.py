"""Patch Airtable Surveyor Email for all records.

Usage:
  python scripts/patch_surveyor_emails.py --dry-run
  python scripts/patch_surveyor_emails.py
  python scripts/patch_surveyor_emails.py --max-records 50

This overwrites the Airtable field configured as ATAIRTABLE_FIELDS.vendor_email
(default: "Surveyor Email").
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from siteowlqa.airtable_client import AirtableClient
from siteowlqa.config import ATAIRTABLE_FIELDS as FIELDS
from siteowlqa.config import load_config


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--email",
        default="maxim.tsitolovsky@walmart.com",
        help="Email to set for all records.",
    )
    p.add_argument(
        "--max-records",
        type=int,
        default=0,
        help="0 means all records.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing to Airtable.",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_config()
    airtable = AirtableClient(cfg)

    records = airtable.list_all_records(max_records=max(0, args.max_records))
    target = args.email.strip()

    to_change = [r for r in records if (r.vendor_email or "").strip().lower() != target.lower()]

    print(f"Airtable field: {FIELDS.vendor_email}")
    print(f"Target email  : {target}")
    print(f"Total records : {len(records)}")
    print(f"Will change   : {len(to_change)}")

    for r in to_change[:20]:
        print(f"  - {r.record_id} | site={r.site_number} | from='{r.vendor_email}'")
    if len(to_change) > 20:
        print(f"  ... and {len(to_change) - 20} more")

    if args.dry_run:
        print("\nDRY RUN: no changes applied.")
        return 0

    for r in to_change:
        airtable.patch_vendor_email(r.record_id, target)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
