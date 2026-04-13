"""reload_reference_db.py — Truncate ReferenceExport and reload from P1 + P2 CSVs.

Mapping (CSV col -> SQL col):
    SelectedSiteID -> ProjectID
    Name           -> Name
    Abreviated_    -> AbbreviatedName
    Part_Number    -> PartNumber
    Manufacturer   -> Manufacturer
    IP_Address     -> IPAddress
    MACAddress     -> MACAddress
    IP___Analog    -> IPAnalog
    Description    -> Description

Run: python scripts/reload_reference_db.py
"""
import sys, time, traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pandas as pd
import pyodbc
from siteowlqa.config import load_config

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
P1 = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\DATA LAKE\Survey DL\Survey_Data_4_06_26_P1.csv')
P2 = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\DATA LAKE\Survey DL\Survey_Data_4_06_26_P2.csv')
CHUNK_SIZE = 10_000

CSV_TO_SQL = {
    'SelectedSiteID': 'ProjectID',
    'Name':           'Name',
    'Abreviated_':    'AbbreviatedName',
    'Part_Number':    'PartNumber',
    'Manufacturer':   'Manufacturer',
    'IP_Address':     'IPAddress',
    'MACAddress':     'MACAddress',
    'IP___Analog':    'IPAnalog',
    'Description':    'Description',
}

INSERT_SQL = """
INSERT INTO dbo.ReferenceExport
    (ProjectID, Name, AbbreviatedName, PartNumber, Manufacturer,
     IPAddress, MACAddress, IPAnalog, Description, LoadDate)
VALUES (?,?,?,?,?,?,?,?,?,?)
"""

LOAD_DATE = datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def none_if_blank(v):
    if v is None:
        return None
    s = str(v).strip()
    return None if s in ('', 'nan', 'NaN', 'None') else s


def chunk_to_rows(df_chunk):
    rows = []
    for _, r in df_chunk.iterrows():
        rows.append((
            none_if_blank(r.get('SelectedSiteID')),
            none_if_blank(r.get('Name')),
            none_if_blank(r.get('Abreviated_')),
            none_if_blank(r.get('Part_Number')),
            none_if_blank(r.get('Manufacturer')),
            none_if_blank(r.get('IP_Address')),
            none_if_blank(r.get('MACAddress')),
            none_if_blank(r.get('IP___Analog')),
            none_if_blank(r.get('Description')),
            LOAD_DATE,
        ))
    return rows


def load_csv(cur, path: Path, label: str) -> int:
    print(f"\n  Loading {label}: {path.name} ({path.stat().st_size/1_000_000:.1f} MB)")
    total = 0
    t0 = time.time()
    for i, chunk in enumerate(pd.read_csv(path, dtype=str, chunksize=CHUNK_SIZE)):
        rows = chunk_to_rows(chunk)
        cur.executemany(INSERT_SQL, rows)
        total += len(rows)
        if (i + 1) % 10 == 0:
            elapsed = time.time() - t0
            rate = total / elapsed
            print(f"    {total:>9,} rows  {elapsed:5.1f}s  ({rate:,.0f} rows/s)")
    elapsed = time.time() - t0
    print(f"  {label} done: {total:,} rows in {elapsed:.1f}s")
    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    for p in (P1, P2):
        if not p.exists():
            print(f"ERROR: file not found: {p}")
            sys.exit(1)

    cfg = load_config()
    conn_str = (
        f"DRIVER={{{cfg.sql_driver}}};"
        f"SERVER={cfg.sql_server};"
        f"DATABASE={cfg.sql_database};"
        f"Trusted_Connection=yes;"
    )

    print(f"Connecting to {cfg.sql_server} / {cfg.sql_database} ...")
    conn = pyodbc.connect(conn_str, autocommit=False)
    cur = conn.cursor()
    cur.fast_executemany = True

    # Pre-truncate count
    cur.execute("SELECT COUNT(*) FROM dbo.ReferenceExport")
    before = cur.fetchone()[0]
    print(f"Rows before truncate: {before:,}")

    # Truncate
    print("Truncating dbo.ReferenceExport ...")
    cur.execute("TRUNCATE TABLE dbo.ReferenceExport")
    conn.commit()
    print("Truncated.")

    # Load
    t_start = time.time()
    try:
        n1 = load_csv(cur, P1, 'P1')
        conn.commit()
        n2 = load_csv(cur, P2, 'P2')
        conn.commit()
    except Exception:
        conn.rollback()
        traceback.print_exc()
        print("\nROLLED BACK — database unchanged from truncated state.")
        sys.exit(1)

    total_time = time.time() - t_start

    # Verify
    cur.execute("SELECT COUNT(*) FROM dbo.ReferenceExport")
    after = cur.fetchone()[0]

    # Quick site sample
    cur.execute("""
        SELECT TOP 10 ProjectID, COUNT(*) as cnt
        FROM dbo.ReferenceExport
        GROUP BY ProjectID
        ORDER BY cnt DESC
    """)
    print("\nTop 10 sites by row count:")
    for r in cur.fetchall():
        print(f"  Site {r[0]:<8} {r[1]:>6,} rows")

    conn.close()

    print(f"\n=== DONE ===")
    print(f"  P1 rows loaded  : {n1:,}")
    print(f"  P2 rows loaded  : {n2:,}")
    print(f"  Total inserted  : {n1+n2:,}")
    print(f"  DB row count    : {after:,}")
    print(f"  Match           : {'YES' if after == n1+n2 else 'NO — MISMATCH'}")
    print(f"  Total time      : {total_time:.1f}s")


if __name__ == '__main__':
    main()
