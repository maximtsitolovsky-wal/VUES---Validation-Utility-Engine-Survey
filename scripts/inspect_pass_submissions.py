"""Inspect one PASS submission for site 9 and one for site 144.

Prints:
- which Airtable records were chosen
- raw file column headers
- whether the 8 canonical grade fields are present in the raw file

This answers: "did the vendor upload include everything needed?"
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from siteowlqa.airtable_client import AirtableClient
from siteowlqa.config import VENDOR_GRADE_COLUMNS, load_config


def _read_headers(path: Path) -> list[str]:
    suf = path.suffix.lower()
    if suf == ".csv":
        df = pd.read_csv(path, nrows=1, dtype=str)
    else:
        df = pd.read_excel(path, sheet_name=0, nrows=1, engine="openpyxl")
    return [str(c) for c in df.columns]


def _presence(headers: list[str]) -> dict[str, bool]:
    lower = {h.strip().lower() for h in headers}
    return {col: (col.strip().lower() in lower) for col in VENDOR_GRADE_COLUMNS}


def main() -> None:
    cfg = load_config()
    airtable = AirtableClient(cfg)
    recs = airtable.list_all_records()

    r9 = next(
        r for r in recs
        if r.site_number.strip() == "9" and r.processing_status.strip().upper() == "PASS"
    )
    r144 = next(
        r for r in recs
        if r.site_number.strip() == "144" and r.processing_status.strip().upper() == "PASS"
    )

    picks = [r9, r144]
    for r in picks:
        p = Path(airtable.download_attachment(r))
        headers = _read_headers(p)
        pres = _presence(headers)

        print("=" * 80)
        print(f"RECORD_ID={r.record_id}")
        print(f"SITE={r.site_number}")
        print(f"STATUS={r.processing_status}")
        print(f"FILE={r.attachment_filename}")
        print(f"PATH={p}")
        print(f"RAW_COL_COUNT={len(headers)}")
        print("\nRAW_HEADERS:")
        for h in headers:
            print(f"  - {h}")

        print("\nCANONICAL_FIELD_PRESENT_IN_RAW:")
        for k, v in pres.items():
            print(f"  - {k}: {v}")


if __name__ == "__main__":
    main()
