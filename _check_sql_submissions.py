"""Check what's in the SQL database for submissions."""
from siteowlqa.config import load_config
from siteowlqa.sql import get_sql_connection

cfg = load_config()

print("Connecting to SQL Server...")
print(f"Server: {cfg.sql_server}")
print(f"Database: {cfg.sql_database}")
print()

with get_sql_connection(cfg) as conn:
    cursor = conn.cursor()
    
    # Check SubmissionLog
    print("=" * 60)
    print("CHECKING dbo.SubmissionLog")
    print("=" * 60)
    cursor.execute("SELECT COUNT(*) as cnt FROM dbo.SubmissionLog")
    row = cursor.fetchone()
    if row:
        print(f"Total rows: {row.cnt}")
    
    # Get all submissions
    cursor.execute("""
        SELECT TOP 100
            SubmissionID,
            RecordID,
            SiteNumber,
            Status,
            Score,
            GradedAt,
            ErrorCount
        FROM dbo.SubmissionLog
        ORDER BY GradedAt DESC
    """)
    
    rows = cursor.fetchall()
    print(f"\nFound {len(rows)} submissions in database:")
    print()
    for i, row in enumerate(rows[:20], 1):
        print(f"{i:2d}. {row.SubmissionID} | Site: {row.SiteNumber:6s} | {row.Status:10s} | Score: {row.Score or 'N/A':>6}")
    
    print()
    print("=" * 60)
    print("STATUS BREAKDOWN")
    print("=" * 60)
    cursor.execute("""
        SELECT Status, COUNT(*) as cnt
        FROM dbo.SubmissionLog
        GROUP BY Status
        ORDER BY Status
    """)
    for row in cursor.fetchall():
        print(f"  {row.Status}: {row.cnt}")
