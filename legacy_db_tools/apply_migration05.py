"""apply_migration05.py -- Apply migration 05 to harden usp_GradeSubmission.

Safe-ish to run on a live database, but worker threads should be idle first.
This script:
  1. Applies sql_migrations/05_harden_usp_GradeSubmission.sql
  2. Verifies the live proc definition contains the new invariant checks
"""

from config import load_config
from sql import get_connection

cfg = load_config()

proc_sql = open(
    r'C:\SiteOwlQA_App\sql_migrations\05_harden_usp_GradeSubmission.sql',
    encoding='utf-8',
).read()

batches = [b.strip() for b in proc_sql.split('\nGO') if b.strip()]

print("=== Phase 1: Applying Migration 05 ===")
with get_connection(cfg, autocommit=True) as conn:
    cur = conn.cursor()
    for i, batch in enumerate(batches, 1):
        if not batch or batch.upper().startswith('USE') or batch.upper().startswith('PRINT'):
            if batch.upper().startswith('PRINT'):
                print(f"  SQL: {batch}")
            continue
        cur.execute(batch)
        print(f"  Batch {i}: OK")

print()
print("=== Phase 2: Verifying live proc ===")
with get_connection(cfg, autocommit=False) as conn:
    cur = conn.cursor()
    cur.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.usp_GradeSubmission'))")
    defn = cur.fetchone()[0] or ''

checks = {
    "stage/reference row count mismatch guard": "IF @StageRows <> @ExpectedRows",
    "mismatch overflow guard": "IF @MismatchRows > @ExpectedRows",
    "score range guard": "IF @Score < 0 OR @Score > 100",
    "error message writeback": "ErrorMessage = @ErrorMessage",
}
for label, needle in checks.items():
    if needle in defn:
        print(f"  [OK] {label}")
    else:
        print(f"  [!!] Missing: {label}")
        raise SystemExit(1)

print()
print("=== Migration 05 complete ===")
