"""cleanup_stage.py -- Delete inflated SubmissionStage rows caused by the missing
WHERE clause bug in usp_LoadSubmissionFromRaw (fixed by Migration 04).

These rows had 930-2170 rows per submission instead of the correct 310.
Deleting them is safe -- they can be reprocessed later against the current
Python-first grading flow if needed.
"""
from siteowlqa.config import load_config
from siteowlqa.sql import get_connection

BAD_SUBMISSIONS = [
    'recIkdWce3idbo3nu',
    'rec17BvW4phkVQcI0',
    'recHECN7d3funjG68',
    'recCvehbjWUrQKjQq',
    'reck37oWLulCKkdvH',
    'recYK5azlqbWdupjL',
    'rec7Q0qdAS7VYivm5',
    'TEST001',
]

cfg = load_config()
with get_connection(cfg, autocommit=True) as conn:
    cur = conn.cursor()

    print("=== Deleting inflated SubmissionStage rows ===")
    for sid in BAD_SUBMISSIONS:
        cur.execute("DELETE FROM dbo.SubmissionStage WHERE SubmissionID = ?", (sid,))
        deleted = cur.rowcount
        print(f"  {sid}: deleted {deleted} rows")

    cur.execute("SELECT COUNT(*) FROM dbo.SubmissionStage")
    remaining = cur.fetchone()[0]
    print(f"\n  SubmissionStage now has {remaining} total rows.")

    # Also clean up their QAResults since those are also based on bad data
    print()
    print("=== Deleting bad QAResults for inflated submissions ===")
    for sid in BAD_SUBMISSIONS:
        cur.execute("DELETE FROM dbo.QAResults WHERE SubmissionID = ?", (sid,))
        deleted = cur.rowcount
        print(f"  {sid}: deleted {deleted} QAResult rows")

    print()
    print("Done! These submissions can be reprocessed later if you still need")
    print("fresh archive/output results under the current Python-first grader.")
