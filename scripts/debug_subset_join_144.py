"""Debug helper: compare one Airtable submission vs reference for site 144.

This script prints rows where the submission is missing Manufacturer but
reference has it, to validate our subset grading approach.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from siteowlqa.airtable_client import AirtableClient
from siteowlqa.config import load_config
from siteowlqa.file_processor import load_vendor_file_with_metadata
from siteowlqa.reference_data import fetch_reference_rows


def _norm(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = out[c].fillna("").astype(str).str.strip().str.upper()
    return out


def main() -> None:
    cfg = load_config()
    airtable = AirtableClient(cfg)

    record_id = "recMtTjdLZwrmb3z1"
    site = "144"

    rec = [r for r in airtable.list_all_records() if r.record_id == record_id][0]
    p = airtable.download_attachment(rec)

    load = load_vendor_file_with_metadata(Path(p), site)
    sub = load.dataframe
    ref = fetch_reference_rows(cfg, site)

    cols = [
        "Name",
        "Abbreviated Name",
        "Part Number",
        "Manufacturer",
        "IP Address",
        "MAC Address",
        "IP / Analog",
        "Description",
    ]

    sub_n = _norm(sub, cols)
    ref_n = _norm(ref, cols)

    join = sub_n.merge(
        ref_n,
        on=["MAC Address", "IP Address"],
        how="left",
        suffixes=("_sub", "_ref"),
    )

    missing_mfg = join[
        (join["Manufacturer_sub"].eq(""))
        & (join["Manufacturer_ref"].fillna("").ne(""))
    ]

    print(f"SUB_ROWS={len(sub_n)}")
    print(f"REF_ROWS={len(ref_n)}")
    print(f"MISSING_MFG_BUT_REF_HAS={len(missing_mfg)}")
    show_cols = [
        "Name_sub",
        "MAC Address",
        "IP Address",
        "Manufacturer_sub",
        "Manufacturer_ref",
        "Part Number_sub",
        "Part Number_ref",
    ]
    print(missing_mfg[show_cols].head(50).to_string(index=False))


if __name__ == "__main__":
    main()
