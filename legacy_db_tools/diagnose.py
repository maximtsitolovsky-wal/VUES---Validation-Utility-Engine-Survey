"""diagnose.py -- One-shot diagnostic for common SiteOwlQA pipeline issues.

Run this manually to surface:
  1. Whether SQL migrations 01/02/03 have been applied (column + proc checks)
  2. Which Airtable fields are causing 422 errors (field-by-field PATCH tests)
  3. SubmissionLog/QAResults/SubmissionStage row counts for recent submissions

Usage:
    python diagnose.py

Safe to run on a live database -- read-only SQL checks + small test PATCH.
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---- load config & logging -------------------------------------------------
from utils import configure_logging
from pathlib import Path
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
configure_logging(log_dir)

import logging
log = logging.getLogger("diagnose")

from config import load_config, ATAIRTABLE_FIELDS as FIELDS
from sql import get_connection
import requests

AIRTABLE_API_BASE = "https://api.airtable.com/v0"


# ---------------------------------------------------------------------------
# SQL Diagnostics
# ---------------------------------------------------------------------------

def check_sql(cfg) -> None:
    print("\n" + "="*60)
    print("SQL DIAGNOSTICS")
    print("="*60)

    with get_connection(cfg, autocommit=False) as conn:
        cur = conn.cursor()

        # 1. Check SubmissionStage has SubmissionID column (Migration 01)
        cur.execute("""
            SELECT COUNT(*) FROM sys.columns
            WHERE object_id = OBJECT_ID('dbo.SubmissionStage')
              AND name = 'SubmissionID'
        """)
        has_col = cur.fetchone()[0] > 0
        status = "[OK] EXISTS" if has_col else "[!!] MISSING"
        print(f"[Migration 01] SubmissionStage.SubmissionID column: {status}")
        if not has_col:
            print("   >> FIX: Run sql_migrations/01_add_submissionid_to_stage.sql")

        # 2. Check usp_LoadSubmissionFromRaw accepts @SubmissionID (Migration 02)
        cur.execute("""
            SELECT COUNT(*) FROM sys.parameters p
            JOIN sys.objects o ON p.object_id = o.object_id
            WHERE o.name = 'usp_LoadSubmissionFromRaw'
              AND p.name = '@SubmissionID'
        """)
        load_ok = cur.fetchone()[0] > 0
        status = "[OK] ACCEPTS @SubmissionID" if load_ok else "[!!] MISSING @SubmissionID param"
        print(f"[Migration 02] usp_LoadSubmissionFromRaw: {status}")
        if not load_ok:
            print("   >> FIX: Run sql_migrations/02_upgrade_usp_LoadSubmissionFromRaw.sql")

        # 3. Check usp_GradeSubmission accepts @SubmissionID (Migration 03)
        cur.execute("""
            SELECT COUNT(*) FROM sys.parameters p
            JOIN sys.objects o ON p.object_id = o.object_id
            WHERE o.name = 'usp_GradeSubmission'
              AND p.name = '@SubmissionID'
        """)
        grade_ok = cur.fetchone()[0] > 0
        status = "[OK] ACCEPTS @SubmissionID" if grade_ok else "[!!] MISSING @SubmissionID param"
        print(f"[Migration 03] usp_GradeSubmission: {status}")
        if not grade_ok:
            print("   >> FIX: Run sql_migrations/03_upgrade_usp_GradeSubmission.sql")

        # 4. Check recent SubmissionLog entries
        print("\n[SubmissionLog] Most recent 10 entries:")
        try:
            cur.execute("""
                SELECT TOP 10 SubmissionID, Status, Score, ReceivedTime
                FROM dbo.SubmissionLog
                ORDER BY ReceivedTime DESC
            """)
            rows = cur.fetchall()
            if not rows:
                print("   (no rows found -- table might be empty or column names differ)")
            for row in rows:
                print(f"   SubmissionID={row[0]} | Status={row[1]} | Score={row[2]} | Time={row[3]}")
        except Exception as exc:
            print(f"   [!!] Could not query SubmissionLog: {exc}")
            print("   >> The column names in read_submission_result (sql.py) may not match your schema.")
            print("   >> Expected columns: Status, Score, ErrorMessage (or Message), ReceivedTime (or CreatedAt)")

        # 5. Check if SubmissionStage has any NULL SubmissionIDs (unfixed rows)
        if has_col:
            cur.execute("""
                SELECT COUNT(*) FROM dbo.SubmissionStage WHERE SubmissionID IS NULL
            """)
            null_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM dbo.SubmissionStage")
            total_count = cur.fetchone()[0]
            print(f"\n[SubmissionStage] Total rows: {total_count} | Rows with NULL SubmissionID: {null_count}")
            if null_count > 0:
                print("   >> NULL SubmissionIDs mean LoadFromRaw is not populating that column.")
                print("   >> FIX: Ensure Migration 02 populates SubmissionID in the INSERT.")


# ---------------------------------------------------------------------------
# Airtable Field Diagnostics
# ---------------------------------------------------------------------------

def check_airtable(cfg) -> None:
    print("\n" + "="*60)
    print("AIRTABLE FIELD DIAGNOSTICS")
    print("="*60)

    base_url = (
        f"{AIRTABLE_API_BASE}/{cfg.airtable_base_id}/"
        f"{requests.utils.quote(cfg.airtable_table_name, safe='')}"
    )
    headers = {
        "Authorization": f"Bearer {cfg.airtable_token}",
        "Content-Type": "application/json",
    }

    # Fetch one real record to use as test subject
    print("Fetching one record for field test...")
    try:
        resp = requests.get(
            base_url, headers=headers,
            params={"pageSize": 1}, timeout=30,
        )
        resp.raise_for_status()
        records = resp.json().get("records", [])
        if not records:
            print("   No records found in Airtable -- cannot run field tests.")
            return
        test_record_id = records[0]["id"]
        print(f"   Using record: {test_record_id}")
    except Exception as exc:
        print(f"   [!!] Could not fetch records: {exc}")
        return

    test_url = f"{base_url}/{test_record_id}"

    # Test each field individually
    test_cases = [
        ("Processing Status (string)",     {FIELDS.status: "PROCESSING"}),
        ("Score as float (0.0)",            {FIELDS.score: 0.0}),
        ("Score as string ('97.5%')",       {FIELDS.score: "97.5%"}),
        ("Fail Summary (text)",             {FIELDS.fail_summary: "[DIAGNOSTIC TEST]"}),
        ("Score float + Fail Summary",      {FIELDS.score: 0.0, FIELDS.fail_summary: "[DIAGNOSTIC TEST]"}),
        ("Score string + Fail Summary",     {FIELDS.score: "97.5%", FIELDS.fail_summary: "[DIAGNOSTIC TEST]"}),
        ("Full payload (float score)",      {FIELDS.status: "PROCESSING", FIELDS.score: 0.0, FIELDS.fail_summary: "[DIAGNOSTIC TEST]"}),
        ("Full payload (string score)",     {FIELDS.status: "PROCESSING", FIELDS.score: "97.5%", FIELDS.fail_summary: "[DIAGNOSTIC TEST]"}),
    ]

    print("\nField PATCH test results:")
    for label, fields in test_cases:
        try:
            r = requests.patch(
                test_url, headers=headers,
                json={"fields": fields}, timeout=15,
            )
            if r.ok:
                print(f"   [OK] {label}")
            else:
                print(f"   [!!] {label} -> HTTP {r.status_code}: {r.text[:300]}")
        except Exception as exc:
            print(f"   [!!] {label} -> Exception: {exc}")

    # Restore status to empty so it goes back to unprocessed (do not leave as PROCESSING)
    try:
        requests.patch(
            test_url, headers=headers,
            json={"fields": {FIELDS.status: ""}}, timeout=15,
        )
        print("   (test record status restored to empty)")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("SiteOwlQA -- Diagnostic Tool")
    print(f"Config: {Path('.env').absolute()}")

    try:
        cfg = load_config()
    except Exception as exc:
        print(f"❌ Config load failed: {exc}")
        sys.exit(1)

    check_sql(cfg)
    check_airtable(cfg)

    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)
    print("If SQL migrations are missing, run the .sql files in sql_migrations/ in order.")
    print("If Airtable fields show [!!], update config.py AirtableFields to match your base.")
    print("")


if __name__ == "__main__":
    main()
