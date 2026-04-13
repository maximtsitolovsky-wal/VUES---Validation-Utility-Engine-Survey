"""check_raw.py -- Show what's currently sitting in SubmissionRaw."""
from config import load_config
from sql import get_connection

cfg = load_config()
with get_connection(cfg, autocommit=False) as conn:
    cur = conn.cursor()

    cur.execute("""
        SELECT SubmissionID, COUNT(*) AS cnt
        FROM dbo.SubmissionRaw
        GROUP BY SubmissionID
        ORDER BY cnt DESC
    """)
    rows = cur.fetchall()
    total = sum(r[1] for r in rows)
    print(f"=== dbo.SubmissionRaw: {len(rows)} distinct SubmissionIDs, {total} total rows ===")
    for r in rows:
        print(f"  SubmissionID={r[0]}  Rows={r[1]}")
