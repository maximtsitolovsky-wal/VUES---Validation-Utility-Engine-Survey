"""db_audit.py - One-shot DB schema + proc audit. Delete after use."""
import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=localhost\SITEOWL;DATABASE=SiteOwlQA;'
    'Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;'
)
cur = conn.cursor()

print('=== SQL Migration State ===\n')

for table in ['SubmissionRaw', 'SubmissionStage', 'SubmissionLog', 'QAResults']:
    cur.execute(
        "SELECT COLUMN_NAME, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION", (table,)
    )
    rows = cur.fetchall()
    if rows:
        print(f'{table}:')
        for r in rows:
            print(f'  {r[0]:<28} nullable={r[1]}')
    else:
        print(f'{table}: TABLE NOT FOUND')
    print()

cur.execute(
    "SELECT name FROM sys.objects WHERE type='P' "
    "AND name IN ('usp_LoadSubmissionFromRaw','usp_GradeSubmission') ORDER BY name"
)
procs = [r[0] for r in cur.fetchall()]
print('Stored procs found:', procs)

for proc in ['usp_LoadSubmissionFromRaw', 'usp_GradeSubmission']:
    cur.execute(
        "SELECT p.name, t.name FROM sys.parameters p "
        "JOIN sys.types t ON p.user_type_id=t.user_type_id "
        "WHERE p.object_id=OBJECT_ID(?)", (proc,)
    )
    params = cur.fetchall()
    status = [(r[0], r[1]) for r in params] if params else 'NO PARAMS (needs migration)'
    print(f'  {proc}: {status}')

conn.close()
print('\nDone.')
