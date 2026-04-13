"""validate_fix.py -- Quick smoke test of the read_submission_result fix.
Reads from real SubmissionLog data and shows what the pipeline will produce.
"""
from config import load_config
from sql import get_connection, read_submission_result
from models import ProcessingStatus

cfg = load_config()
print("=== Validating read_submission_result fix ===")
print()

with get_connection(cfg, autocommit=False) as conn:
    cur = conn.cursor()

    # Grab the 5 most recent distinct SubmissionIDs from SubmissionLog
    cur.execute("""
        SELECT DISTINCT TOP 5 SubmissionID
        FROM dbo.SubmissionLog
        ORDER BY SubmissionID DESC
    """)
    submission_ids = [r[0] for r in cur.fetchall()]

for sid in submission_ids:
    with get_connection(cfg, autocommit=False) as conn:
        cur = conn.cursor()
        result = read_submission_result(cur, sid)
    status_str = result.status.value
    score_str  = f"{result.score:.1f}%" if result.score is not None else "N/A"
    airtable_score = f"{result.score:.1f}%" if result.score is not None else "(not written)"
    print(f"  SubmissionID : {sid}")
    print(f"  Status       : {status_str}")
    print(f"  Score        : {score_str}")
    print(f"  Airtable val : {airtable_score}")
    print(f"  Message      : {result.message[:80] if result.message else '(none)'}")
    print()

print("Done. If Status shows PASS or FAIL (not ERROR) and Score looks right, the fix works!")
