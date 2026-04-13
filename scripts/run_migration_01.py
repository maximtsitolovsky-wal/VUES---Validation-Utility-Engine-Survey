"""run_migration_01.py - Adds SubmissionID to SubmissionRaw. Run once, then delete."""
import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    r'SERVER=localhost\SITEOWL;DATABASE=SiteOwlQA;'
    'Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;',
    autocommit=True,
)
cur = conn.cursor()

print('Migration 01: Adding SubmissionID to dbo.SubmissionRaw...')

cur.execute("""
    IF NOT EXISTS (
        SELECT 1 FROM sys.columns
        WHERE object_id = OBJECT_ID('dbo.SubmissionRaw') AND name = 'SubmissionID'
    )
    BEGIN
        ALTER TABLE dbo.SubmissionRaw ADD SubmissionID NVARCHAR(200) NULL;
        PRINT 'Column added.';
    END
    ELSE
        PRINT 'Column already exists - skipped.';
""")

cur.execute("""
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID('dbo.SubmissionRaw')
          AND name = 'IX_SubmissionRaw_SubmissionID'
    )
    BEGIN
        CREATE NONCLUSTERED INDEX IX_SubmissionRaw_SubmissionID
            ON dbo.SubmissionRaw (SubmissionID);
        PRINT 'Index created.';
    END
    ELSE
        PRINT 'Index already exists - skipped.';
""")

# Verify
cur.execute(
    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
    "WHERE TABLE_NAME='SubmissionRaw' AND COLUMN_NAME='SubmissionID'"
)
if cur.fetchone():
    print('PASS: SubmissionRaw.SubmissionID is present.')
else:
    print('FAIL: Column was not added - check SQL Server permissions.')

conn.close()
print('Done.')