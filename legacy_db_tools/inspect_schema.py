"""inspect_schema.py -- Dump SubmissionLog column names and one sample row."""
from config import load_config
from sql import get_connection

cfg = load_config()
with get_connection(cfg, autocommit=False) as conn:
    cur = conn.cursor()

    cur.execute(
        "SELECT name FROM sys.columns "
        "WHERE object_id = OBJECT_ID('dbo.SubmissionLog') ORDER BY column_id"
    )
    print("=== dbo.SubmissionLog columns ===")
    for (col_name,) in cur.fetchall():
        print(f"  {col_name}")

    cur.execute("SELECT TOP 1 * FROM dbo.SubmissionLog ORDER BY ReceivedTime DESC")
    row = cur.fetchone()
    if row:
        names = [d[0] for d in cur.description]
        print()
        print("=== Most recent row ===")
        for n, v in zip(names, row):
            print(f"  {n!s:30s} = {v!r}")
    else:
        print("(no rows in SubmissionLog)")
