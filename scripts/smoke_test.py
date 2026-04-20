"""smoke_test.py — Full system readiness check for SiteOwlQA.

Run this before starting main.py for the first time, or after any changes.
Prints a clear PASS/FAIL result for each check.

Covers:
  - Python version
  - Package imports (siteowlqa.* — current package structure)
  - Config load (user profile + .env)
  - BigQuery connection + device_survey_task_details
  - Airtable API reachability
  - Element LLM Gateway HTTP ping (if configured)
  - Required directories exist and are writable
  - Correction output directories (if configured)
  - Reference workbook file (if excel mode)
  - Scout Airtable (if configured)
"""

from __future__ import annotations

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
print("=== VUES Smoke Test ===")
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
    "siteowlqa.airtable_client",
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
        "airtable_base_id":    cfg.airtable_base_id,
        "airtable_table_name": cfg.airtable_table_name,
        "airtable_token":      cfg.airtable_token,
    }
    info = {
        "reference_source":      cfg.reference_source,
        "gcp_project":           cfg.gcp_project,
        "bigquery_dataset":      cfg.bigquery_dataset,
        "poll_interval_seconds": cfg.poll_interval_seconds,
        "worker_threads":        cfg.worker_threads,
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

    ok("SMTP removed — Airtable automation handles email")

    if VENDOR_TO_SQL_COLUMNS:
        ok(f"VENDOR_TO_SQL_COLUMNS has {len(VENDOR_TO_SQL_COLUMNS)} entries")
    else:
        fail("VENDOR_TO_SQL_COLUMNS", "Empty")

except Exception as exc:
    fail("config load", str(exc))
    import traceback; traceback.print_exc()

# ---------------------------------------------------------------------------
# 4. BigQuery connection
# ---------------------------------------------------------------------------
section("BigQuery")
if cfg and cfg.reference_source == "bigquery":
    try:
        from google.cloud import bigquery
        from google.oauth2 import service_account

        if cfg.gcp_credentials_path:
            creds = service_account.Credentials.from_service_account_file(
                cfg.gcp_credentials_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            client = bigquery.Client(project=cfg.gcp_project, credentials=creds)
            ok(f"credentials loaded from {cfg.gcp_credentials_path}")
        else:
            client = bigquery.Client(project=cfg.gcp_project)
            ok("using Application Default Credentials")

        # Test query to verify table access
        test_query = f"""
            SELECT COUNT(*) as cnt
            FROM `{cfg.gcp_project}.{cfg.bigquery_dataset}.device_survey_task_details`
        """
        result = client.query(test_query).result()
        row_count = list(result)[0].cnt
        ok(f"device_survey_task_details accessible — {row_count:,} rows")

    except ImportError:
        fail("BigQuery", "google-cloud-bigquery not installed")
    except Exception as exc:
        fail("BigQuery connection", str(exc))
elif cfg and cfg.reference_source == "excel":
    ok("reference_source=excel — BigQuery not required")
else:
    print("  (skipped — config not loaded)")

# ---------------------------------------------------------------------------
# 5. Airtable API
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
        print(f"  X {f}")
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
