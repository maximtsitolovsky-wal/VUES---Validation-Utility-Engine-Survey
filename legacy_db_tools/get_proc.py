"""get_proc.py -- Dump the actual stored proc definitions from the live DB."""
from config import load_config
from sql import get_connection

cfg = load_config()
with get_connection(cfg, autocommit=False) as conn:
    cur = conn.cursor()
    for proc in ('usp_LoadSubmissionFromRaw', 'usp_GradeSubmission'):
        cur.execute(
            "SELECT OBJECT_DEFINITION(OBJECT_ID(?))",
            (f'dbo.{proc}',),
        )
        row = cur.fetchone()
        print(f"\n{'='*60}")
        print(f"  {proc}")
        print('='*60)
        if row and row[0]:
            print(row[0])
        else:
            print("(definition not found)")
