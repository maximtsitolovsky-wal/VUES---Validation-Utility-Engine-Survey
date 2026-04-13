from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from siteowlqa.config import load_config
from siteowlqa.reference_data import normalize_reference_dataframe
from siteowlqa.sql import get_connection
from siteowlqa.utils import canon_site_id

REFERENCE_RAW_TABLE = "dbo.ReferenceRaw"
REFERENCE_EXPORT_TABLE = "dbo.ReferenceExport"
TARGET_COLUMNS = [
    "ProjectID",
    "Name",
    "AbbreviatedName",
    "Description",
    "PartNumber",
    "Manufacturer",
    "IPAddress",
    "MACAddress",
    "IPAnalog",
]
RAW_INSERT_SQL = f"""
    INSERT INTO {REFERENCE_RAW_TABLE} (
        ProjectID,
        Name,
        AbbreviatedName,
        Description,
        PartNumber,
        Manufacturer,
        IPAddress,
        MACAddress,
        IPAnalog
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""
EXPORT_INSERT_SQL = f"""
    INSERT INTO {REFERENCE_EXPORT_TABLE} (
        ProjectID,
        Name,
        AbbreviatedName,
        Description,
        PartNumber,
        Manufacturer,
        IPAddress,
        MACAddress,
        IPAnalog
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _canon(value: object) -> str:
    text = canon_site_id(value)
    if text == "0":
        return ""
    return text


def load_reference_rows_from_workbook() -> pd.DataFrame:
    cfg = load_config()
    workbook_path = cfg.reference_workbook_path
    if workbook_path is None:
        raise SystemExit("No reference workbook configured.")
    if not workbook_path.exists():
        raise SystemExit(f"Reference workbook not found: {workbook_path}")

    raw_df = pd.read_excel(
        workbook_path,
        sheet_name=cfg.reference_workbook_sheet or 0,
        dtype=str,
        engine="openpyxl",
    )
    # IMPORTANT:
    # SQL uses ProjectID as the site lookup key.
    # Airtable provides Site Number, and in the cleaned workbook this lives in
    # column A (e.g. 'SelectedSiteID'). We map that -> SQL ProjectID.
    normalized = normalize_reference_dataframe(raw_df)

    # Pull the site-id column directly from the raw workbook (not the normalized
    # dataframe), because the workbook might not have a canonical 'Project ID'
    # column that matches Airtable Site Number.
    site_col = cfg.reference_workbook_site_id_column
    if site_col not in raw_df.columns:
        available = ", ".join(str(c) for c in list(raw_df.columns)[:25])
        raise SystemExit(
            f"Workbook missing configured site-id column '{site_col}'. "
            f"Available columns include: {available}"
        )
    normalized["ProjectID"] = raw_df[site_col].map(canon_site_id)

    normalized = normalized.rename(
        columns={
            "Name": "Name",
            "Abbreviated Name": "AbbreviatedName",
            "Description": "Description",
            "Part Number": "PartNumber",
            "Manufacturer": "Manufacturer",
            "IP Address": "IPAddress",
            "MAC Address": "MACAddress",
            "IP / Analog": "IPAnalog",
        }
    )
    for col in TARGET_COLUMNS:
        if col not in normalized.columns:
            normalized[col] = ""
        normalized[col] = normalized[col].map(_canon)
    return normalized[TARGET_COLUMNS].copy()


def main() -> None:
    cfg = load_config()
    df = load_reference_rows_from_workbook()
    insert_rows = list(df.itertuples(index=False, name=None))

    with get_connection(cfg, autocommit=False) as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {REFERENCE_RAW_TABLE}")
        before_raw_count = int(cur.fetchone()[0])
        cur.execute(f"SELECT COUNT(*) FROM {REFERENCE_EXPORT_TABLE}")
        before_export_count = int(cur.fetchone()[0])

        print(f"WORKBOOK={cfg.reference_workbook_path}")
        print(f"SHEET={cfg.reference_workbook_sheet or '<first>'}")
        print(f"RAW_TABLE={REFERENCE_RAW_TABLE}")
        print(f"EXPORT_TABLE={REFERENCE_EXPORT_TABLE}")
        print(f"BEFORE_RAW_COUNT={before_raw_count}")
        print(f"BEFORE_EXPORT_COUNT={before_export_count}")
        print(f"WORKBOOK_COUNT={len(insert_rows)}")

        cur.fast_executemany = True
        cur.execute(f"TRUNCATE TABLE {REFERENCE_RAW_TABLE}")
        cur.execute(f"TRUNCATE TABLE {REFERENCE_EXPORT_TABLE}")
        if insert_rows:
            cur.executemany(RAW_INSERT_SQL, insert_rows)
            cur.executemany(EXPORT_INSERT_SQL, insert_rows)

        cur.execute(f"SELECT COUNT(*) FROM {REFERENCE_RAW_TABLE}")
        after_raw_count = int(cur.fetchone()[0])
        cur.execute(f"SELECT COUNT(*) FROM {REFERENCE_EXPORT_TABLE}")
        after_export_count = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM dbo.vw_ReferenceNormalized")
        view_count = int(cur.fetchone()[0])

        print(f"AFTER_RAW_COUNT={after_raw_count}")
        print(f"AFTER_EXPORT_COUNT={after_export_count}")
        print(f"VIEW_COUNT={view_count}")

        if after_raw_count != len(insert_rows):
            raise RuntimeError(
                f"ReferenceRaw row-count mismatch: inserted={len(insert_rows)} table={after_raw_count}"
            )
        if after_export_count != len(insert_rows):
            raise RuntimeError(
                f"ReferenceExport row-count mismatch: inserted={len(insert_rows)} table={after_export_count}"
            )
        if view_count != after_export_count:
            raise RuntimeError(
                f"View row-count mismatch: export={after_export_count} view={view_count}"
            )

        cur.execute(
            """
            SELECT TOP 5 ProjectID, Name, PartNumber, Manufacturer
            FROM dbo.vw_ReferenceNormalized
            ORDER BY ProjectID, Name
            """
        )
        print("SAMPLE_ROWS=")
        for row in cur.fetchall():
            print("  " + " | ".join("" if v is None else str(v) for v in row))


if __name__ == "__main__":
    main()
