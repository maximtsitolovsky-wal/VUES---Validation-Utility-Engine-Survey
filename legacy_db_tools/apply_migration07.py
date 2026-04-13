"""Apply migration 07 to relax fatal row-count mismatch behavior in usp_GradeSubmission.

This script:
  1. Applies sql_migrations/07_relax_row_count_error_in_usp_GradeSubmission.sql
  2. Verifies the live proc definition no longer hard-fails on @StageRows <> @ExpectedRows
  3. Verifies a ROW_COUNT_MISMATCH diagnostic QAResults insert exists
"""

from config import load_config
from sql import get_connection

cfg = load_config()

proc_sql = open(
    r"C:\SiteOwlQA_App\sql_migrations\07_relax_row_count_error_in_usp_GradeSubmission.sql",
    encoding="utf-8",
).read()

batches = [b.strip() for b in proc_sql.split("\nGO") if b.strip()]

print("=== Phase 1: Applying Migration 07 ===")
with get_connection(cfg, autocommit=True) as conn:
    cur = conn.cursor()
    for i, batch in enumerate(batches, 1):
        if not batch or batch.upper().startswith("USE") or batch.upper().startswith("PRINT"):
            if batch.upper().startswith("PRINT"):
                print(f"  SQL: {batch}")
            continue
        cur.execute(batch)
        print(f"  Batch {i}: OK")

print()
print("=== Phase 2: Verifying live proc ===")
with get_connection(cfg, autocommit=False) as conn:
    cur = conn.cursor()
    cur.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.usp_GradeSubmission'))")
    defn = cur.fetchone()[0] or ""

checks_present = {
    "row count diagnostic issue type": "'ROW_COUNT_MISMATCH'",
    "placeholder comparison fix retained": "NULLIF(RefAbbrev, '0')",
    "comparison bounds guard": "Row mismatch count exceeds comparison bounds",
}
for label, needle in checks_present.items():
    if needle in defn:
        print(f"  [OK] {label}")
    else:
        print(f"  [!!] Missing: {label}")
        raise SystemExit(1)

checks_absent = {
    "fatal row count guard removed": "IF @StageRows <> @ExpectedRows\n    BEGIN\n        SET @PassFail = 'ERROR'",
}
for label, needle in checks_absent.items():
    if needle in defn:
        print(f"  [!!] Still present: {label}")
        raise SystemExit(1)
    print(f"  [OK] {label}")

print()
print("=== Migration 07 complete ===")
