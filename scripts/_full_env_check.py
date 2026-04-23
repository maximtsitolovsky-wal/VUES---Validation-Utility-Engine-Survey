"""Full environment and orchestration health check for VUES."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

print("=" * 60)
print("VUES ENVIRONMENT & ORCHESTRATION CHECK")
print("=" * 60)

# Track results
passed = []
failed = []
warned = []

def ok(name, detail=""):
    print(f"  ✓ {name}" + (f" ({detail})" if detail else ""))
    passed.append(name)

def fail(name, reason):
    print(f"  ✗ {name}: {reason}")
    failed.append(name)

def warn(name, reason):
    print(f"  ⚠ {name}: {reason}")
    warned.append(name)

# ---------------------------------------------------------------------------
# 1. Python Environment
# ---------------------------------------------------------------------------
print("\n[1] PYTHON ENVIRONMENT")
print(f"  Executable: {sys.executable}")
print(f"  Version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

if sys.version_info >= (3, 11):
    ok("Python version", f"{sys.version_info.major}.{sys.version_info.minor}")
else:
    fail("Python version", f"Need >=3.11, got {sys.version_info.major}.{sys.version_info.minor}")

# Check venv
if ".venv" in sys.executable:
    ok("Virtual environment", "using .venv")
else:
    warn("Virtual environment", "not using project .venv")

# ---------------------------------------------------------------------------
# 2. Dependencies
# ---------------------------------------------------------------------------
print("\n[2] DEPENDENCIES")
deps = [
    ("pyairtable", "Airtable API"),
    ("pandas", "Data processing"),
    ("openpyxl", "XLSX read/write"),
    ("win32com.client", "Windows COM (pywin32)"),
    ("google.cloud.bigquery", "BigQuery"),
    ("google.auth", "Google Auth"),
    ("db_dtypes", "BigQuery dtypes"),
    ("requests", "HTTP client"),
    ("httpx", "Async HTTP"),
    ("pydantic_ai", "LLM framework"),
    ("openai", "OpenAI SDK"),
    ("dotenv", "Environment loader"),
]

for mod, desc in deps:
    try:
        __import__(mod)
        ok(mod, desc)
    except ImportError as e:
        fail(mod, str(e))

# ---------------------------------------------------------------------------
# 3. SITEOWLQA Modules
# ---------------------------------------------------------------------------
print("\n[3] SITEOWLQA MODULES")
modules = [
    "siteowlqa.config",
    "siteowlqa.models",
    "siteowlqa.utils",
    "siteowlqa.archive",
    "siteowlqa.memory",
    "siteowlqa.file_processor",
    "siteowlqa.reference_data",
    "siteowlqa.python_grader",
    "siteowlqa.airtable_client",
    "siteowlqa.poll_airtable",
    "siteowlqa.submission_queue",
    "siteowlqa.queue_worker",
    "siteowlqa.metrics",
    "siteowlqa.metrics_worker",
    "siteowlqa.dashboard",
    "siteowlqa.dashboard_exec",
    "siteowlqa.correction_worker",
    "siteowlqa.scout_sync_worker",
    "siteowlqa.main",
]

for mod in modules:
    try:
        __import__(mod)
        ok(mod)
    except Exception as e:
        fail(mod, str(e)[:60])

# ---------------------------------------------------------------------------
# 4. Configuration
# ---------------------------------------------------------------------------
print("\n[4] CONFIGURATION")
cfg = None
try:
    from siteowlqa.config import load_config, VENDOR_TO_SQL_COLUMNS
    cfg = load_config()
    ok("Config loaded")
    
    # Check required values
    required = {
        "airtable_token": bool(cfg.airtable_token),
        "airtable_base_id": bool(cfg.airtable_base_id),
        "airtable_table_name": bool(cfg.airtable_table_name),
    }
    for k, v in required.items():
        if v:
            ok(f"config.{k}", "set")
        else:
            fail(f"config.{k}", "missing or empty")
    
    print(f"  Reference source: {cfg.reference_source}")
    print(f"  GCP project: {cfg.gcp_project}")
    print(f"  Poll interval: {cfg.poll_interval_seconds}s")
    print(f"  Worker threads: {cfg.worker_threads}")
    
    if VENDOR_TO_SQL_COLUMNS:
        ok("VENDOR_TO_SQL_COLUMNS", f"{len(VENDOR_TO_SQL_COLUMNS)} vendors")
    else:
        fail("VENDOR_TO_SQL_COLUMNS", "empty")
        
except Exception as e:
    fail("Config load", str(e))

# ---------------------------------------------------------------------------
# 5. Directories
# ---------------------------------------------------------------------------
print("\n[5] DIRECTORIES")
if cfg:
    dirs = {
        "temp_dir": cfg.temp_dir,
        "output_dir": cfg.output_dir,
        "log_dir": cfg.log_dir,
        "archive_dir": cfg.archive_dir,
        "submissions_dir": cfg.submissions_dir,
    }
    for name, path in dirs.items():
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".probe"
            probe.write_text("ok")
            probe.unlink()
            ok(name, str(path))
        except Exception as e:
            fail(name, str(e)[:50])

# ---------------------------------------------------------------------------
# 6. Airtable API
# ---------------------------------------------------------------------------
print("\n[6] AIRTABLE API")
if cfg and cfg.airtable_token:
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
            ok("Airtable API", f"table '{cfg.airtable_table_name}' accessible")
        else:
            fail("Airtable API", f"HTTP {resp.status_code}")
    except Exception as e:
        fail("Airtable API", str(e)[:50])

    # Scout Airtable
    if cfg.scout_airtable_token:
        try:
            scout_url = f"https://api.airtable.com/v0/{cfg.scout_airtable_base_id}/{cfg.scout_airtable_table_name}"
            sresp = requests.get(
                scout_url,
                headers={"Authorization": f"Bearer {cfg.scout_airtable_token}"},
                params={"maxRecords": 1},
                timeout=10,
            )
            if sresp.status_code == 200:
                ok("Scout Airtable", "accessible")
            else:
                warn("Scout Airtable", f"HTTP {sresp.status_code}")
        except Exception as e:
            warn("Scout Airtable", str(e)[:50])
    else:
        ok("Scout Airtable", "not configured (optional)")

# ---------------------------------------------------------------------------
# 7. BigQuery
# ---------------------------------------------------------------------------
print("\n[7] BIGQUERY")
if cfg and cfg.reference_source in ("bigquery", "bigquery_with_fallback"):
    try:
        from google.cloud import bigquery
        from google.oauth2 import service_account
        
        if cfg.gcp_credentials_path:
            creds = service_account.Credentials.from_service_account_file(
                cfg.gcp_credentials_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            client = bigquery.Client(project=cfg.gcp_project, credentials=creds)
            ok("BigQuery credentials", cfg.gcp_credentials_path)
        else:
            client = bigquery.Client(project=cfg.gcp_project)
            ok("BigQuery credentials", "Application Default Credentials")
        
        # Test query
        test_query = f"""
            SELECT COUNT(*) as cnt
            FROM `{cfg.gcp_project}.{cfg.bigquery_dataset}.device_survey_task_details`
            LIMIT 1
        """
        result = list(client.query(test_query).result())
        row_count = result[0].cnt if result else 0
        ok("BigQuery query", f"{row_count:,} rows in device_survey_task_details")
        
    except Exception as e:
        if cfg.reference_source == "bigquery_with_fallback":
            warn("BigQuery", f"{str(e)[:50]} (will fall back to Excel)")
        else:
            fail("BigQuery", str(e)[:50])
elif cfg:
    ok("BigQuery", f"not required (reference_source={cfg.reference_source})")

# ---------------------------------------------------------------------------
# 8. Orchestration Components
# ---------------------------------------------------------------------------
print("\n[8] ORCHESTRATION COMPONENTS")
try:
    from siteowlqa.airtable_client import AirtableClient
    if cfg:
        at = AirtableClient(cfg)
        ok("AirtableClient", "instantiated")
except Exception as e:
    fail("AirtableClient", str(e)[:50])

try:
    from siteowlqa.archive import Archive
    if cfg:
        archive = Archive(cfg.archive_dir)
        ok("Archive", "instantiated")
except Exception as e:
    fail("Archive", str(e)[:50])

try:
    from siteowlqa.memory import Memory
    if cfg:
        memory = Memory(archive)
        ok("Memory", "instantiated")
except Exception as e:
    fail("Memory", str(e)[:50])

try:
    from siteowlqa.submission_queue import SubmissionQueue
    queue = SubmissionQueue()
    ok("SubmissionQueue", "instantiated")
except Exception as e:
    fail("SubmissionQueue", str(e)[:50])

try:
    from siteowlqa.correction_worker import CorrectionWorker
    ok("CorrectionWorker", "importable")
except Exception as e:
    fail("CorrectionWorker", str(e)[:50])

try:
    from siteowlqa.metrics_worker import MetricsRefreshWorker
    ok("MetricsRefreshWorker", "importable")
except Exception as e:
    fail("MetricsRefreshWorker", str(e)[:50])

try:
    from siteowlqa.scout_sync_worker import ScoutSyncWorker
    ok("ScoutSyncWorker", "importable")
except Exception as e:
    fail("ScoutSyncWorker", str(e)[:50])

# ---------------------------------------------------------------------------
# 9. Grading Pipeline Test
# ---------------------------------------------------------------------------
print("\n[9] GRADING PIPELINE (dry run)")
if cfg:
    try:
        from siteowlqa.reference_data import fetch_reference_rows
        from siteowlqa.python_grader import grade_submission_in_python
        import pandas as pd
        
        # Create a minimal test submission
        test_df = pd.DataFrame({
            "Name": ["Test Camera 1"],
            "Abbreviated Name": ["TC1"],
            "Part Number": ["PN-001"],
            "Manufacturer": ["Acme"],
            "IP Address": ["192.168.1.1"],
            "MAC Address": ["00:11:22:33:44:55"],
            "IP / Analog": ["IP"],
            "Description": ["Test"],
        })
        
        # Try grading (will fail due to no reference, but tests the pipeline)
        result = grade_submission_in_python(
            cfg=cfg,
            submission_df=test_df,
            submission_id="test-dry-run",
            site_number="99999",  # Non-existent site
        )
        ok("Grading pipeline", f"executed (result: {result.result.status.value})")
    except Exception as e:
        fail("Grading pipeline", str(e)[:60])

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  ✓ Passed: {len(passed)}")
print(f"  ⚠ Warned: {len(warned)}")
print(f"  ✗ Failed: {len(failed)}")

if failed:
    print("\nFAILED ITEMS:")
    for f in failed:
        print(f"  - {f}")
    print("\n❌ FIX THESE BEFORE RUNNING main.py")
    sys.exit(1)
else:
    print("\n✅ ALL CHECKS PASSED — System ready!")
    print("\n  Run:  python main.py")
    sys.exit(0)
