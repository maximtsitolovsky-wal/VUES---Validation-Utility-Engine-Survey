"""apply_migration06.py -- Apply migration 06 placeholder comparison fix."""

from config import load_config
from sql import get_connection

cfg = load_config()

proc_sql = open(
    r'C:\SiteOwlQA_App\sql_migrations\06_fix_placeholder_comparison_for_siteowl.sql',
    encoding='utf-8',
).read()

batches = [b.strip() for b in proc_sql.split('\nGO') if b.strip()]

print("=== Phase 1: Applying Migration 06 ===")
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
    "AbbreviatedName placeholder normalization": "NULLIF(RefAbbrev, '0')",
    "Description placeholder normalization": "NULLIF(RefDesc, '0')",
    "row count guard": "IF @StageRows <> @ExpectedRows",
}
for label, needle in checks.items():
    if needle in defn:
        print(f"  [OK] {label}")
    else:
        print(f"  [!!] Missing: {label}")
        raise SystemExit(1)

print()
print("=== Migration 06 complete ===")
