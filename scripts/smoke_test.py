"""smoke_test.py — Full system readiness check for SiteOwlQA.

Run this before starting main.py for the first time, or after any changes.
Prints a clear PASS/FAIL result for each check.
"""
import sys
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

failed: list[str] = []


def ok(label: str) -> None:
    print(f'  OK   {label}')


def fail(label: str, reason: str) -> None:
    print(f'  FAIL {label}: {reason}')
    failed.append(label)


# ---------------------------------------------------------------------------
# Module imports
# ---------------------------------------------------------------------------
print('=== SiteOwlQA Smoke Test ===')
print(f'Python: {sys.version}')
print()
print('--- Module imports ---')
for mod in [
    'models', 'utils', 'config', 'archive', 'memory',
    'reviewer', 'metrics', 'dashboard', 'file_processor',
    'emailer', 'airtable_client', 'sql',
    'submission_queue', 'queue_worker', 'metrics_worker',
    'poll_airtable', 'main',
]:
    try:
        __import__(mod)
        ok(f'import {mod}')
    except Exception as e:
        fail(f'import {mod}', str(e))


# ---------------------------------------------------------------------------
# Config load
# ---------------------------------------------------------------------------
print()
print('--- Config ---')
cfg = None
try:
    import config as cfg_mod
    cfg = cfg_mod.load_config()

    # Always-required fields
    required_fields = {
        'sql_server':          cfg.sql_server,
        'sql_database':        cfg.sql_database,
        'airtable_base_id':    cfg.airtable_base_id,
        'airtable_table_name': cfg.airtable_table_name,
    }
    # Informational (not validated as required)
    info_fields = {
        'smtp_enabled':        str(cfg.smtp_enabled),
        'poll_interval':       f'{cfg.poll_interval_seconds}s',
        'worker_threads':      str(cfg.worker_threads),
        'temp_dir':            str(cfg.temp_dir),
        'output_dir':          str(cfg.output_dir),
        'log_dir':             str(cfg.log_dir),
        'archive_dir':         str(cfg.archive_dir),
    }

    all_fields = {**required_fields, **info_fields}
    for k, v in all_fields.items():
        print(f'  {k:<25}: {v}')

    # Only flag if required fields are placeholders
    placeholder_fields = [
        k for k, v in required_fields.items()
        if str(v).upper().strip() in ('FILL_THIS_IN', 'REPLACE_WITH_BASE_ID',
                                      'REPLACE_WITH_TABLE_NAME', '')
    ]

    if placeholder_fields:
        fail('config values', f'Still placeholder: {placeholder_fields}')
    else:
        ok('config all required values populated')

    # When SMTP is enabled, also validate SMTP fields
    if cfg.smtp_enabled:
        smtp_fields = {'smtp_user': cfg.smtp_user, 'from_email': cfg.from_email}
        smtp_missing = [k for k, v in smtp_fields.items() if not str(v).strip()]
        if smtp_missing:
            fail('smtp config', f'SMTP_ENABLED=true but these are blank: {smtp_missing}')
        else:
            ok('SMTP config populated')
    else:
        ok('SMTP disabled — Airtable automation handles vendor emails')

except Exception as e:
    fail('config load', str(e))
    import traceback; traceback.print_exc()


# ---------------------------------------------------------------------------
# SQL Server connection
# ---------------------------------------------------------------------------
print()
print('--- SQL Server ---')
conn = None
try:
    import pyodbc
    conn = pyodbc.connect(cfg.sql_connection_string, timeout=5)
    cur = conn.cursor()
    cur.execute('SELECT DB_NAME(), @@SERVERNAME')
    row = cur.fetchone()
    ok(f'connection DB={row[0]} Server={row[1]}')
except Exception as e:
    fail('SQL connection', str(e))


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------
print()
print('--- Schema ---')
if conn:
    try:
        cur = conn.cursor()

        # SubmissionRaw.SubmissionID (migration 01)
        cur.execute(
            "SELECT COUNT(1) FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME='SubmissionRaw' AND COLUMN_NAME='SubmissionID'"
        )
        if cur.fetchone()[0]:
            ok('SubmissionRaw.SubmissionID exists')
        else:
            fail('SubmissionRaw.SubmissionID', 'Missing - run run_migration_01.py')

        # SubmissionStage.SubmissionID
        cur.execute(
            "SELECT COUNT(1) FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME='SubmissionStage' AND COLUMN_NAME='SubmissionID'"
        )
        if cur.fetchone()[0]:
            ok('SubmissionStage.SubmissionID exists')
        else:
            fail('SubmissionStage.SubmissionID', 'Column missing')

        # SubmissionLog required columns
        for col in ['ErrorMessage', 'ReceivedTime', 'Status', 'Score']:
            cur.execute(
                "SELECT COUNT(1) FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_NAME='SubmissionLog' AND COLUMN_NAME=?", (col,)
            )
            if cur.fetchone()[0]:
                ok(f'SubmissionLog.{col} exists')
            else:
                fail(f'SubmissionLog.{col}', 'Column missing')

        # QAResults.QAResultID
        cur.execute(
            "SELECT COUNT(1) FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME='QAResults' AND COLUMN_NAME='QAResultID'"
        )
        if cur.fetchone()[0]:
            ok('QAResults.QAResultID exists')
        else:
            fail('QAResults.QAResultID', 'Column missing')

        # Stored proc signatures
        proc_params = {
            'usp_LoadSubmissionFromRaw': ['@SubmissionID', '@VendorEmail', '@SiteNumber'],
            'usp_GradeSubmission':       ['@SubmissionID'],
        }
        for proc, required in proc_params.items():
            cur.execute(
                "SELECT p.name FROM sys.parameters p "
                "WHERE p.object_id = OBJECT_ID(?)", (proc,)
            )
            actual = {r[0] for r in cur.fetchall()}
            missing = [p for p in required if p not in actual]
            if not missing:
                ok(f'{proc} params OK')
            else:
                fail(proc, f'Missing params: {missing}')

        conn.close()
        conn = None

    except Exception as e:
        fail('schema check', str(e))
else:
    print('  (skipped - no SQL connection)')


# ---------------------------------------------------------------------------
# Column mapping sanity
# ---------------------------------------------------------------------------
print()
print('--- Column mapping ---')
try:
    from config import VENDOR_TO_SQL_COLUMNS
    if not VENDOR_TO_SQL_COLUMNS:
        fail('VENDOR_TO_SQL_COLUMNS', 'Empty')
    else:
        ok(f'VENDOR_TO_SQL_COLUMNS has {len(VENDOR_TO_SQL_COLUMNS)} entries')
except Exception as e:
    fail('VENDOR_TO_SQL_COLUMNS', str(e))


# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------
print()
print('--- Directories ---')
if cfg:
    for d in [cfg.temp_dir, cfg.output_dir, cfg.log_dir, cfg.archive_dir]:
        try:
            d.mkdir(parents=True, exist_ok=True)
            ok(f'{d.name}/')
        except Exception as e:
            fail(str(d), str(e))
else:
    print('  (skipped - config not loaded)')


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------
print()
print('=' * 50)
if failed:
    print(f'RESULT: {len(failed)} issue(s) - fix before running main.py:')
    for f in failed:
        print(f'  * {f}')
    sys.exit(1)
else:
    print('RESULT: ALL CHECKS PASSED - system is ready!')
    print('  Run:  python main.py')