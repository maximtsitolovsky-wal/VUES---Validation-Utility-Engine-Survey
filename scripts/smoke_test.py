"""smoke_test.py — Full system readiness check for SiteOwlQA.

Run this before starting main.py for the first time, or after any changes.
Prints a clear PASS/FAIL result for each check.

Covers:
  - Python version
  - Package imports (siteowlqa.* — current package structure)
  - Config load (user profile + .env)
  - ODBC driver availability
  - SQL Server connection + dbo.vw_ReferenceNormalized (current schema)
  - Airtable API reachability
  - SMTP socket connect (if enabled)
  - Element LLM Gateway HTTP ping (if configured)
  - Required directories exist and are writable
  - Correction output directories (if configured)
  - Reference workbook file (if excel mode)
  - Scout Airtable (if configured)
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap — works from any CWD
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------
_failed: list[str] = []
_warned: list[str] = []


def ok(label: str, detail: str = "") -> None:
    suffix = f"  ({detail})" if detail else ""
    print(f"  OK   {label}{suffix}")


def warn(label: str, reason: str) -> None:
    print(f"  WARN {label}: {reason}")
    _warned.append(label)


def fail(label: str, reason: str) -> None:
    print(f"  FAIL {label}: {reason}")
    _failed.append(label)


def section(title: str) -> None:
    print()
    print(f"--- {title} ---")


# ---------------------------------------------------------------------------
# 1. Python version
# ---------------------------------------------------------------------------
print("=== SiteOwlQA Smoke Test ===")
print(f"Python : {sys.version}")
print(f"Project: {_PROJECT_ROOT}")

section("Python version")
if sys.version_info >= (3, 11):
    ok(f"Python {sys.version_info.major}.{sys.version_info.minor}")
else:
    fail(
        "Python version",
        f"Requires >= 3.11, got {sys.version_info.major}.{sys.version_info.minor}",
    )

# ---------------------------------------------------------------------------
# 2. Package imports
# ---------------------------------------------------------------------------
section("Package imports")
_MODULES = [
    "siteowlqa.models",
    "siteowlqa.utils",
    "siteowlqa.config",
    "siteowlqa.archive",
    "siteowlqa.memory",
    "siteowlqa.reviewer",
    "siteowlqa.metrics",
    "siteowlqa.dashboard",
    "siteowlqa.file_processor",
    "siteowlqa.emailer",
    "siteowlqa.airtable_client",
    "siteowlqa.sql",
    "siteowlqa.python_grader",
    "siteowlqa.submission_queue",
    "siteowlqa.queue_worker",
    "siteowlqa.metrics_worker",
    "siteowlqa.poll_airtable",
    "siteowlqa.correction_worker",
    "siteowlqa.reference_data",
    "siteowlqa.main",
]
for mod in _MODULES:
    try:
        __import__(mod)
        ok(f"import {mod}")
    except Exception as exc:
        fail(f"import {mod}", str(exc))

# ---------------------------------------------------------------------------
# 3. Config
# ---------------------------------------------------------------------------
section("Config")
cfg = None
try:
    from siteowlqa.config import load_config, VENDOR_TO_SQL_COLUMNS

    cfg = load_config()

    required = {
        "sql_server":          cfg.sql_server,
        "sql_database":        cfg.sql_database,
        "airtable_base_id":    cfg.airtable_base_id,
        "airtable_table_name": cfg.airtable_table_name,
        "airtable_token":      cfg.airtable_token,
    }
    info = {
        "reference_source":      cfg.reference_source,
        "poll_interval_seconds": cfg.poll_interval_seconds,
        "worker_threads":        cfg.worker_threads,
        "smtp_enabled":          cfg.smtp_enabled,
        "temp_dir":              cfg.temp_dir,
        "output_dir":            cfg.output_dir,
        "log_dir":               cfg.log_dir,
        "archive_dir":           cfg.archive_dir,
    }

    for k, v in {**required, **info}.items():
        print(f"  {k:<30}: {v}")

    _PLACEHOLDERS = {"", "FILL_THIS_IN", "REPLACE_WITH_BASE_ID", "REPLACE_WITH_TABLE_NAME"}
    bad = [k for k, v in required.items() if str(v).strip().upper() in _PLACEHOLDERS]
    if bad:
        fail("config required values", f"Still placeholder: {bad}")
    else:
        ok("config required values populated")

    if cfg.smtp_enabled:
        smtp_missing = [k for k, v in {"smtp_user": cfg.smtp_user, "from_email": cfg.from_email}.items() if not str(v).strip()]
        if smtp_missing:
            fail("smtp config", f"smtp_enabled but blank: {smtp_missing}")
        else:
            ok("SMTP config populated")
    else:
        ok("SMTP disabled")

    if VENDOR_TO_SQL_COLUMNS:
        ok(f"VENDOR_TO_SQL_COLUMNS has {len(VENDOR_TO_SQL_COLUMNS)} entries")
    else:
        fail("VENDOR_TO_SQL_COLUMNS", "Empty")

except Exception as exc:
    fail("config load", str(exc))
    import traceback; traceback.print_exc()

# ---------------------------------------------------------------------------
# 4. ODBC driver
# ---------------------------------------------------------------------------
section("ODBC driver")
try:
    import pyodbc

    drivers = pyodbc.drivers()
    if cfg:
        if cfg.sql_driver in drivers:
            ok(f"driver present: {cfg.sql_driver}")
        else:
            fail(
                "ODBC driver",
                f"'{cfg.sql_driver}' not found. Available: {drivers}",
            )
    else:
        ok(f"pyodbc importable — available drivers: {drivers}")
except Exception as exc:
    fail("pyodbc", str(exc))

# ---------------------------------------------------------------------------
# 5. SQL Server connection + schema
# ---------------------------------------------------------------------------
section("SQL Server")
_sql_conn = None
if cfg:
    try:
        import pyodbc as _pyodbc

        _sql_conn = _pyodbc.connect(cfg.sql_connection_string, timeout=8)
        cur = _sql_conn.cursor()
        cur.execute("SELECT DB_NAME(), @@SERVERNAME")
        row = cur.fetchone()
        ok(f"connected — DB={row[0]}  Server={row[1]}")
    except Exception as exc:
        fail("SQL connection", str(exc))
else:
    print("  (skipped — config not loaded)")

section("SQL schema")
if _sql_conn:
    try:
        cur = _sql_conn.cursor()

        # Primary reference view used by sql.py
        cur.execute(
            "SELECT COUNT(1) FROM INFORMATION_SCHEMA.VIEWS "
            "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='vw_ReferenceNormalized'"
        )
        if cur.fetchone()[0]:
            ok("dbo.vw_ReferenceNormalized view exists")
        else:
            fail("dbo.vw_ReferenceNormalized", "View missing — check SQL migrations")

        # Verify view has data
        try:
            cur.execute("SELECT COUNT(*) FROM dbo.vw_ReferenceNormalized")
            row_count = cur.fetchone()[0]
            if row_count > 0:
                ok(f"dbo.vw_ReferenceNormalized has {row_count:,} row(s)")
            else:
                warn("dbo.vw_ReferenceNormalized", "View exists but is empty — reference data not loaded")
        except Exception as exc:
            fail("dbo.vw_ReferenceNormalized row count", str(exc))

        # Verify columns expected by sql.py are present in the view
        _EXPECTED_COLS = {"ProjectID", "Name", "AbbreviatedName", "PartNumber",
                          "Manufacturer", "IPAddress", "MACAddress", "IPAnalog", "Description"}
        cur.execute(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='vw_ReferenceNormalized'"
        )
        actual_cols = {r[0] for r in cur.fetchall()}
        missing_cols = _EXPECTED_COLS - actual_cols
        if missing_cols:
            fail("vw_ReferenceNormalized columns", f"Missing: {sorted(missing_cols)}")
        else:
            ok("vw_ReferenceNormalized columns match sql.py expectations")

        # ReferenceRaw backing table
        cur.execute(
            "SELECT COUNT(1) FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='ReferenceRaw'"
        )
        if cur.fetchone()[0]:
            ok("dbo.ReferenceRaw table exists")
        else:
            warn("dbo.ReferenceRaw", "Table not found — may be under a different name")

        _sql_conn.close()
        _sql_conn = None

    except Exception as exc:
        fail("SQL schema check", str(exc))
        import traceback; traceback.print_exc()
else:
    print("  (skipped — no SQL connection)")

# ---------------------------------------------------------------------------
# 6. Airtable API
# ---------------------------------------------------------------------------
section("Airtable API")
if cfg and cfg.airtable_token and cfg.airtable_base_id:
    try:
        import requests

        url = f"https://api.airtable.com/v0/{cfg.airtable_base_id}/{cfg.airtable_table_name}"
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {cfg.airtable_token}"},
            params={"maxRecords": 1},
            timeout=10,
        )
        if resp.status_code == 200:
            ok(f"Airtable reachable — table '{cfg.airtable_table_name}' responded 200")
        elif resp.status_code == 401:
            fail("Airtable auth", "401 Unauthorized — check airtable_token")
        elif resp.status_code == 403:
            fail("Airtable auth", "403 Forbidden — token lacks read access to this base/table")
        elif resp.status_code == 404:
            fail("Airtable table", f"404 Not Found — check airtable_base_id / airtable_table_name (got: {resp.status_code})")
        else:
            warn("Airtable", f"Unexpected status {resp.status_code}: {resp.text[:200]}")
    except Exception as exc:
        fail("Airtable request", str(exc))

    # Scout Airtable (optional second source)
    if cfg.scout_airtable_token and cfg.scout_airtable_base_id:
        try:
            scout_url = f"https://api.airtable.com/v0/{cfg.scout_airtable_base_id}/{cfg.scout_airtable_table_name}"
            sresp = requests.get(
                scout_url,
                headers={"Authorization": f"Bearer {cfg.scout_airtable_token}"},
                params={"maxRecords": 1},
                timeout=10,
            )
            if sresp.status_code == 200:
                ok(f"Scout Airtable reachable — table '{cfg.scout_airtable_table_name}' responded 200")
            else:
                warn("Scout Airtable", f"Status {sresp.status_code} — check SCOUT_* env vars")
        except Exception as exc:
            fail("Scout Airtable request", str(exc))
    else:
        ok("Scout Airtable not configured (optional)")
else:
    print("  (skipped — config not loaded or token/base_id missing)")

# ---------------------------------------------------------------------------
# 7. SMTP (socket connect only — no email sent)
# ---------------------------------------------------------------------------
section("SMTP")
if cfg and cfg.smtp_enabled and cfg.smtp_server:
    try:
        with socket.create_connection((cfg.smtp_server, cfg.smtp_port), timeout=8) as sock:
            banner = sock.recv(256).decode(errors="replace").strip()
        ok(f"SMTP socket connected — {cfg.smtp_server}:{cfg.smtp_port}  banner={banner[:80]!r}")
    except Exception as exc:
        fail(f"SMTP socket {cfg.smtp_server}:{cfg.smtp_port}", str(exc))
elif cfg and not cfg.smtp_enabled:
    ok("SMTP disabled — skipped")
else:
    print("  (skipped — config not loaded)")

# ---------------------------------------------------------------------------
# 8. Element LLM Gateway (HTTP ping, no prompt sent)
# ---------------------------------------------------------------------------
section("Element LLM Gateway")
if cfg and cfg.element_llm_gateway_url:
    try:
        import requests as _req

        verify: bool | str = True
        if cfg.wmt_ca_path:
            verify = cfg.wmt_ca_path

        # Ping the base URL — a 200, 401, or 404 all prove the host is reachable
        resp = _req.get(cfg.element_llm_gateway_url, timeout=8, verify=verify)
        if resp.status_code < 500:
            ok(f"LLM Gateway reachable — {cfg.element_llm_gateway_url} → HTTP {resp.status_code}")
        else:
            warn("LLM Gateway", f"HTTP {resp.status_code} — gateway may be down")
    except Exception as exc:
        fail("LLM Gateway request", str(exc))
else:
    ok("LLM Gateway not configured (optional)")

# ---------------------------------------------------------------------------
# 9. Required directories — exist + writable
# ---------------------------------------------------------------------------
section("Directories")
if cfg:
    _dirs = {
        "temp_dir":       cfg.temp_dir,
        "output_dir":     cfg.output_dir,
        "log_dir":        cfg.log_dir,
        "archive_dir":    cfg.archive_dir,
        "submissions_dir": cfg.submissions_dir,
    }
    for name, path in _dirs.items():
        try:
            path.mkdir(parents=True, exist_ok=True)
            # Writability probe
            _probe = path / ".smoke_test_probe"
            _probe.write_text("ok")
            _probe.unlink()
            ok(f"{name}: {path}")
        except Exception as exc:
            fail(f"{name} ({path})", str(exc))
else:
    print("  (skipped — config not loaded)")

# ---------------------------------------------------------------------------
# 10. Correction output directories (OneDrive paths — optional)
# ---------------------------------------------------------------------------
section("Correction output directories")
if cfg:
    _correction_dirs = {
        "correction_corrected_dir": cfg.correction_corrected_dir,
        "correction_log_dir":       cfg.correction_log_dir,
        "correction_raw_dir":       cfg.correction_raw_dir,
    }
    any_configured = any(v is not None for v in _correction_dirs.values())
    if any_configured:
        for name, path in _correction_dirs.items():
            if path is None:
                warn(name, "Not configured — will fall back to output_dir/corrections/")
                continue
            if path.exists():
                try:
                    _probe = path / ".smoke_test_probe"
                    _probe.write_text("ok")
                    _probe.unlink()
                    ok(f"{name}: {path}")
                except Exception as exc:
                    fail(f"{name} writability ({path})", str(exc))
            else:
                fail(f"{name}", f"Path does not exist: {path}  (OneDrive synced?)")
    else:
        ok("No correction dirs configured — will use output_dir/corrections/ at runtime")
else:
    print("  (skipped — config not loaded)")

# ---------------------------------------------------------------------------
# 11. Reference workbook (if excel or auto mode)
# ---------------------------------------------------------------------------
section("Reference workbook")
if cfg:
    if cfg.reference_source in ("excel", "auto") and cfg.reference_workbook_path:
        wb_path = cfg.reference_workbook_path
        if wb_path.exists():
            ok(f"Workbook found: {wb_path}")
            if cfg.reference_workbook_sheet:
                ok(f"Sheet configured: '{cfg.reference_workbook_sheet}'")
            else:
                warn("reference_workbook_sheet", "Blank — will use first sheet")
        else:
            fail("reference_workbook_path", f"File not found: {wb_path}")
    elif cfg.reference_source == "excel" and not cfg.reference_workbook_path:
        fail("reference_workbook_path", "REFERENCE_SOURCE=excel but no workbook path configured")
    else:
        ok(f"Reference source: '{cfg.reference_source}' — workbook not required")
else:
    print("  (skipped — config not loaded)")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print("=" * 55)
if _failed:
    print(f"RESULT: {len(_failed)} FAILURE(S) — fix before running main.py:")
    for f in _failed:
        print(f"  ✗ {f}")
    if _warned:
        print(f"\n  + {len(_warned)} warning(s) (non-fatal):")
        for w in _warned:
            print(f"  ! {w}")
    sys.exit(1)
else:
    if _warned:
        print(f"RESULT: ALL CHECKS PASSED — {len(_warned)} warning(s), review above.")
        for w in _warned:
            print(f"  ! {w}")
    else:
        print("RESULT: ALL CHECKS PASSED — system is ready!")
    print()
    print("  Run:  python main.py")
