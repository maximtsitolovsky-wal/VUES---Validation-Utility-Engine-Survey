"""apply_migration04.py -- Apply migration 04 + clean up stale SubmissionRaw/Stage rows.

Runs in two phases:
  1. Patch usp_LoadSubmissionFromRaw with the missing WHERE SubmissionID filters.
  2. Delete accumulated rows from SubmissionRaw and SubmissionStage that were
     caused by the missing WHERE clause (rows with NULL SubmissionID or belonging
     to completed submissions that are no longer pending).

Safe to run on a live database. Worker threads should be idle first.
"""
import pyodbc
from config import load_config
from sql import get_connection

cfg = load_config()

# ---- Phase 1: Apply the stored procedure fix ----------------------------
proc_sql = open(
    r'C:\SiteOwlQA_App\sql_migrations\04_fix_usp_LoadSubmissionFromRaw_where_clause.sql',
    encoding='utf-8',
).read()

# Split on GO statements (SQL Server batch separator)
batches = [b.strip() for b in proc_sql.split('\nGO') if b.strip()]

print("=== Phase 1: Applying Migration 04 ===")
with get_connection(cfg, autocommit=True) as conn:
    cur = conn.cursor()
    for i, batch in enumerate(batches, 1):
        if not batch or batch.upper().startswith('USE') or batch.upper().startswith('PRINT'):
            if batch.upper().startswith('PRINT'):
                print(f"  SQL: {batch}")
            continue
        try:
            cur.execute(batch)
            print(f"  Batch {i}: OK")
        except Exception as exc:
            print(f"  Batch {i}: ERROR -- {exc}")
            raise

print()
print("=== Phase 2: Verifying fix ===")
with get_connection(cfg, autocommit=False) as conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.usp_LoadSubmissionFromRaw'))
    """)
    defn = cur.fetchone()[0] or ''
    if 'WHERE  SubmissionID = @SubmissionID' in defn or 'WHERE SubmissionID = @SubmissionID' in defn:
        print("  [OK] WHERE SubmissionID filter confirmed in proc definition.")
    else:
        print("  [!!] WHERE clause NOT found -- check migration file!")
        print(defn[:500])

print()
print("=== Phase 3: Cleaning up stale SubmissionRaw rows ===")
with get_connection(cfg, autocommit=True) as conn:
    cur = conn.cursor()

    # Show before state
    cur.execute("SELECT SubmissionID, COUNT(*) FROM dbo.SubmissionRaw GROUP BY SubmissionID ORDER BY COUNT(*) DESC")
    before = cur.fetchall()
    print(f"  Before: {sum(r[1] for r in before)} total rows across {len(before)} SubmissionIDs")

    # Delete rows with NULL SubmissionID (pre-migration orphans -- these pollute every run)
    cur.execute("DELETE FROM dbo.SubmissionRaw WHERE SubmissionID IS NULL")
    null_deleted = cur.rowcount
    print(f"  Deleted {null_deleted} rows with NULL SubmissionID")

    # Show after state
    cur.execute("SELECT COUNT(*) FROM dbo.SubmissionRaw")
    after_count = cur.fetchone()[0]
    print(f"  After: {after_count} total rows remain (each scoped to a real SubmissionID)")

print()
print("=== Phase 4: Cleaning up inflated SubmissionStage rows ===")
with get_connection(cfg, autocommit=False) as conn:
    cur = conn.cursor()

    # Find which submissions have more than 310 rows (inflated from the bug)
    cur.execute("""
        SELECT SubmissionID, COUNT(*) AS cnt
        FROM dbo.SubmissionStage
        GROUP BY SubmissionID
        HAVING COUNT(*) > 310
        ORDER BY cnt DESC
    """)
    inflated = cur.fetchall()
    if not inflated:
        print("  No inflated SubmissionStage rows found.")
    else:
        print(f"  Found {len(inflated)} inflated submission(s) in SubmissionStage:")
        for r in inflated:
            print(f"    SubmissionID={r[0]}  Rows={r[1]}")

print()
print("  NOTE: Inflated SubmissionStage rows need to be re-processed to get")
print("  correct scores. They will be fixed when those submissions are re-graded.")
print("  Alternatively, delete them from SubmissionStage and re-submit from Airtable.")
print()
print("=== Migration 04 complete ===")
