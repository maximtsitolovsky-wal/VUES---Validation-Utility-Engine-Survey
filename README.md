# VUES - Validation Utility Engine Survey

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![Platform Windows](https://img.shields.io/badge/platform-Windows-lightgrey)
![License MIT](https://img.shields.io/badge/license-MIT-green)
![BigQuery](https://img.shields.io/badge/data-BigQuery-orange)

> **Enterprise-grade vendor QA pipeline** for automated submission validation.
>
> Airtable → Python (parallel workers) → BigQuery reference lookup → Grading results

## ✨ Features

- **Parallel Processing** — Multiple worker threads process submissions concurrently
- **BigQuery Integration** — Reference data from GSOC production tables
- **Single-Instance Lock** — Prevents duplicate polling when cloning the repo  
- **Auto-Recovery** — Stuck records are recovered on startup
- **Real-time Dashboard** — HTML dashboards with vendor metrics
- **Autonomous Correction** — Post-pass correction for high-scoring submissions

## 🚀 Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd SiteOwlQA_App
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Configure (interactive wizard)
python -m siteowlqa.setup_config

# Verify setup
python scripts/smoke_test.py

# Run
python main.py
```

> ⚠️ **Single Instance**: Only one pipeline should poll a given Airtable base.
> The application uses a lock file to prevent duplicate instances.

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Configuration Guide](docs/configuration.md) | Detailed setup instructions |
| [Clone and Run](docs/clone-and-run.md) | Onboarding for new team members |
| [Contributing](CONTRIBUTING.md) | Development workflow |
| [Architecture](prompts/architect_prompt.md) | System design decisions |

---

## Architecture Overview

```
 Airtable Form
      ↓  (vendor submits XLSX/CSV via Airtable form)

 Python Polling Service  (poll every 60 seconds)
      ↓  download attachment
      ↓  normalize columns, overwrite Project ID ← Airtable Site Number
      ↓  fetch site-scoped reference rows from BigQuery
      ↓  compare canonical headers in Python
      ↓  derive PASS / FAIL / ERROR + score in Python
      ↓  PATCH Airtable Processing Status (PASS / FAIL / ERROR)
      ↓  Airtable automation sends vendor email (no SMTP in pipeline)
      ↓  archive raw file → archive/submissions/YYYY/MM/DD/
      ↓  save execution + review JSON
      ↓  refresh vendor_metrics.csv + submission_history.csv
      ↓  refresh HTML dashboards
      ↓  extract lesson if failure
```

### Module Map

| File | Purpose |
|---|---|
| `src/siteowlqa/main.py` | Poll loop, worker lifecycle, crash recovery, dashboard open |
| `src/siteowlqa/poll_airtable.py` | 15-step per-record orchestrator |
| `src/siteowlqa/config.py` | ALL env var + user config access — centralized |
| `src/siteowlqa/models.py` | All domain types (AirtableRecord, SubmissionResult…) |
| `src/siteowlqa/utils.py` | Logging setup, ID generation, safe file delete |
| `src/siteowlqa/airtable_client.py` | Airtable REST API (fetch, download, status update) |
| `src/siteowlqa/file_processor.py` | XLSX/CSV load, header normalization, ProjectID overwrite |
| `src/siteowlqa/bigquery_provider.py` | BigQuery connection + site-scoped reference fetch |
| `src/siteowlqa/python_grader.py` | Python-side grading engine (canonical header comparison) |
| `src/siteowlqa/reference_data.py` | Reference data loader with warm cache |
| `src/siteowlqa/reviewer.py` | Internal static code reviewer |
| `src/siteowlqa/archive.py` | Append-only JSON archive + raw file storage |
| `src/siteowlqa/memory.py` | Tag+keyword lesson retrieval |
| `src/siteowlqa/metrics.py` | Compute metrics, export CSVs |
| `src/siteowlqa/metrics_worker.py` | Single-owner metrics refresh thread |
| `src/siteowlqa/dashboard.py` | Generate HTML dashboards from CSVs |
| `src/siteowlqa/dashboard_exec.py` | Executive dashboard builder |
| `src/siteowlqa/local_dashboard_server.py` | Localhost no-cache HTTP server |
| `src/siteowlqa/submission_queue.py` | In-process dedup submission queue |
| `src/siteowlqa/queue_worker.py` | Worker thread: QUEUED → PROCESSING → result |
| `src/siteowlqa/correction_worker.py` | Autonomous post-pass correction thread |
| `src/siteowlqa/correction_state.py` | Idempotent correction state DB |

---

## Stage 1: Core Pipeline

### Step-by-Step: What Happens Per Submission

1. **Poll** — `main.py` calls Airtable every 60 seconds
2. **Fetch** — `airtable_client.get_pending_records()` returns records where Processing Status is blank, `NEW`, or `Pending`
3. **Validate** — Vendor Email, Site Number, and Attachment URL must all be present
4. **Memory check** — `memory.recall()` surfaces prior lessons relevant to this type of run
5. **Download** — XLSX or CSV attachment saved to `temp/`
6. **Normalize** — `file_processor.load_vendor_file()` standardizes headers case-insensitively
7. **Overwrite** — `Project ID` column is always replaced with Airtable `Site Number`
8. **Fetch reference** — load site-scoped source rows from SQL Server
9. **Grade in Python** — compare only canonical headers using fingerprint matching
10. **Build fail details** — generate row mismatch / missing / extra diagnostics
11. **Email** — PASS email (no score) or FAIL email (score + CSV attachment)
12. **Airtable update** — PATCH Processing Status to PASS / FAIL / ERROR

---

## Stage 2: Governance, Archive, and Metrics

14. **Submission archive** — raw vendor file copied to `archive/submissions/YYYY/MM/DD/`, metadata saved as JSON
15. **Execution archive** — `ExecutionRecord` JSON saved to `archive/executions/`
16. **Review** — `reviewer.py` evaluates the run for architecture/business rule issues
17. **Review archive** — `ReviewResult` JSON saved to `archive/reviews/`
18. **Metrics refresh** — `metrics.refresh_all_metrics()` rewrites 3 CSV files in `output/`
19. **Dashboard refresh** — `dashboard.refresh_dashboards()` rewrites 2 HTML files in `output/`
20. **Lesson extraction** — on FAIL/ERROR with HIGH/CRITICAL review issues, saves a lesson to `archive/lessons/`

---

## Project Structure

```
SiteOwlQA_App/
├── main.py                        # entry point (delegates to src/siteowlqa/main.py)
├── pyproject.toml                 # project metadata and build config
├── requirements.txt               # pip-compatible dependency list
├── .env                           # non-secret runtime settings (never commit)
├── .env.example                   # template — copy to .env
│
├── src/siteowlqa/                 # main application package
│   ├── main.py                    # poll loop, worker lifecycle, crash recovery
│   ├── poll_airtable.py           # per-record 15-step orchestrator
│   ├── config.py                  # all env var + user config access
│   ├── models.py                  # domain types (AirtableRecord, SubmissionResult…)
│   ├── utils.py                   # logging setup, ID generation
│   ├── airtable_client.py         # Airtable REST API (fetch, download, PATCH)
│   ├── file_processor.py          # XLSX/CSV loader + header normalization
│   ├── sql.py                     # SQL connection + reference fetch
│   ├── python_grader.py           # Python-side grading engine
│   ├── reference_data.py          # reference data loader + cache
│   ├── reviewer.py                # internal static code reviewer
│   ├── archive.py                 # append-only JSON + raw file archive
│   ├── memory.py                  # lesson tag/keyword retrieval
│   ├── metrics.py                 # CSV metric computation
│   ├── metrics_worker.py          # single-writer metrics refresh thread
│   ├── dashboard.py               # HTML dashboard generation
│   ├── dashboard_exec.py          # executive dashboard builder
│   ├── local_dashboard_server.py  # localhost no-cache HTTP server
│   ├── submission_queue.py        # in-process submission queue
│   ├── queue_worker.py            # worker thread (QUEUED → result)
│   ├── correction_worker.py       # autonomous post-pass correction thread
│   ├── correction_state.py        # idempotent correction state DB
│   ├── post_pass_correction.py    # post-pass field correction logic
│   ├── setup_config.py            # interactive config wizard entry point
│   └── user_config.py             # user config read/write (~/.siteowlqa/)
│
├── ops/windows/                   # Windows launchers and scheduler scripts
│   ├── launch_siteowlqa_dashboard.ps1  # PRIMARY: start + rebuild + open browser
│   ├── start_siteowlqa_background.ps1  # start main.py in background only
│   ├── stop_siteowlqa_background.ps1   # stop main.py
│   ├── run_siteowlqa.bat               # foreground / debug (shows live output)
│   ├── setup_scheduler.bat             # register Windows Task Scheduler (admin)
│   └── README.md                       # ops script documentation
│
├── tools/                         # developer/utility scripts
│   └── run_dashboard_server.py    # standalone localhost dashboard server
│
├── scripts/                       # one-off utilities and backfill helpers
├── tests/                         # pytest test suite
├── docs/                          # extended documentation
├── logs/                          # rotating log files (auto-created)
├── temp/                          # downloaded attachments (auto-cleaned)
├── output/                        # CSV exports + HTML dashboards
└── archive/
    ├── submissions/               # YYYY/MM/DD/<id>_meta.json + raw file
    ├── executions/                # <execution_id>.json
    ├── reviews/                   # <execution_id>_review.json
    └── lessons/                   # LESSON_NNN.json
```

---

## Quick Start Setup

> New teammate onboarding? See **[`docs/clone-and-run.md`](./docs/clone-and-run.md)** for the full step-by-step guide.

### 1. Clone and create the virtual environment

```bat
git clone https://github.com/maximtsitolovsky-wal/VUES---Validation-Utility-Engine-Survey.git
cd VUES---Validation-Utility-Engine-Survey

python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
```

> ℹ️ All launchers auto-detect `.venv\Scripts\python.exe`. If not found they fall back to `python` on your PATH.

### 2. Run the secrets wizard

Stores credentials in `~/.siteowlqa/config.json` — **never committed to the repo**:

```bat
.venv\Scripts\python -m siteowlqa.setup_config
```

Prompts you for:
- SQL Server connection details
- Airtable API token, base ID, and table name
- (Optional) LLM Gateway credentials
- (Optional) Reference data workbook path

### 3. Launch

**Recommended — double-click the Desktop shortcut:**
```
SiteOwlQA Launcher  (Desktop shortcut)
```
This starts the grading pipeline, builds the dashboard, and opens it in your browser automatically.

**Or run the launcher script directly from PowerShell:**
```powershell
powershell -ExecutionPolicy Bypass -File ops\windows\launch_siteowlqa_dashboard.ps1
```

**Foreground / debug mode (shows live log output):**
```bat
ops\windows\run_siteowlqa.bat
```

---

## Configuration

**See [`docs/configuration.md`](./docs/configuration.md) for complete setup details**, including:
- How to get Airtable tokens and base IDs
- How to configure SMTP for email
- How to set up Element LLM Gateway
- Reference data workbook setup
- Troubleshooting common errors

1. In Airtable, look at the tabs at the top of the page
2. The tab name is your table name
3. Use the exact name, including capital letters and spaces

---

## Running the Pipeline

### Daily Operation (Windows)

| What | How |
|---|---|
| **Start everything** (recommended) | Double-click **SiteOwlQA Launcher** on the Desktop |
| Start via terminal | `powershell -ExecutionPolicy Bypass -File ops\windows\launch_siteowlqa_dashboard.ps1` |
| Start pipeline only (no browser) | `powershell -ExecutionPolicy Bypass -File ops\windows\start_siteowlqa_background.ps1` |
| Stop the pipeline | `powershell -ExecutionPolicy Bypass -File ops\windows\stop_siteowlqa_background.ps1` |
| Foreground / debug | `ops\windows\run_siteowlqa.bat` |

The launcher does three things in sequence:
1. Starts `main.py` in the background (or confirms it is already running)
2. Rebuilds the executive dashboard from current data
3. Opens `http://127.0.0.1:8765/executive_dashboard.html` in your browser

**See [`ops/windows/README.md`](./ops/windows/README.md)** for complete launcher documentation.

### 24/7 Automatic Operation

To make the pipeline run automatically at system startup:

1. Right-click: `ops\windows\setup_scheduler.bat`
2. Select: "Run as administrator"
3. Follow the prompts
4. Restart your computer to test

After setup, the pipeline runs automatically whenever Windows starts, even when no user is logged in.

### Monitoring Logs

Logs are written to:
```
C:\SiteOwlQA_App\logs\siteowlqa.stdout.log
```

You should see output like:
```
2025-05-01 09:00:00 | INFO | main | SiteOwlQA pipeline starting...
2025-05-01 09:00:00 | INFO | config | Config loaded from ~/.siteowlqa/config.json
2025-05-01 09:00:00 | INFO | main | Polling Airtable every 60 seconds...
2025-05-01 09:00:01 | INFO | airtable_client | Found 0 pending submission(s).
```

If you see config errors:
- "User configuration not found" → run `python -m siteowlqa.setup_config`
- SQL connection error → verify SQL credentials in `~/.siteowlqa/config.json`
- Airtable auth error → verify token and base ID in config

---

## Where Logs Are Written

Log files are saved to: `C:\SiteOwlQA_App\logs\siteowl_qa.log`

The log file rotates automatically at 10MB. Up to 5 old log files are kept.

To view the latest log:
```cmd
type C:\SiteOwlQA_App\logs\siteowl_qa.log
```

Or open it in Notepad.

Each log line looks like:
```
2025-05-01 09:00:00,123 | INFO     | main            | SiteOwlQA pipeline starting...
2025-05-01 09:01:43,456 | INFO     | poll_airtable   | === START execution=EX_20250501_090143 record=recABC123 ...
2025-05-01 09:01:44,789 | INFO     | sql             | Inserted 42 rows into SubmissionRaw
2025-05-01 09:01:45,111 | INFO     | sql             | Stored proc dbo.usp_LoadSubmissionFromRaw completed
2025-05-01 09:01:46,222 | INFO     | sql             | Stored proc dbo.usp_GradeSubmission completed
2025-05-01 09:01:46,333 | INFO     | sql             | Grade result: status=PASS score=98.5
2025-05-01 09:01:47,444 | INFO     | airtable_client | Airtable automation will send PASS email to vendor
2025-05-01 09:01:47,555 | INFO     | airtable_client | Record recABC123 → Processing Status = 'PASS'
2025-05-01 09:01:48,666 | INFO     | archive         | Submission metadata archived: SUB001_meta.json
2025-05-01 09:01:48,777 | INFO     | metrics         | submission_history.csv updated: 1 rows
2025-05-01 09:01:48,888 | INFO     | dashboard       | vendor_metrics.html generated
2025-05-01 09:01:49,000 | INFO     | poll_airtable   | === END execution=EX_20250501_090143 status=PASS score=98.5 rows=42 duration=5.87s ===
```

---

## Legacy DB Tools

Legacy proc-era SQL migration and forensic helpers were moved to `legacy_db_tools/`.
They are kept only for historical investigation and should not be referenced by
active grading or new development.

---

## Testing Instructions

### Test with one PASS submission

1. Create a vendor CSV/XLSX with all required columns:
   ```
   Project ID, Plan ID, Name, Abbreviated Name, Part Number,
   Manufacturer, IP Address, MAC Address, IP / Analog, Description
   ```
2. Fill in values that exactly match your `dbo.ReferenceExport` data
3. Submit through the Airtable form with a real vendor email
4. Leave `Processing Status` blank
5. Wait up to 60 seconds
6. Confirm in logs: `status=PASS`
7. Check vendor email inbox for PASS email
8. Check Airtable: `Processing Status` should now say `PASS`
9. Check `archive/submissions/YYYY/MM/DD/` for the metadata JSON
10. Check `output/submission_history.csv` for a new row
11. Check `output/vendor_metrics.html` in your browser

### Test with one FAIL submission

1. Create a vendor CSV/XLSX with values that DO NOT match ReferenceExport
2. Submit through Airtable
3. Wait up to 60 seconds
4. Confirm in logs: `status=FAIL score=XX.X`
5. Check vendor email: should contain `Fail`, a score percentage, and a CSV attachment
6. Check `output/QA_Errors_<submission_id>.csv` for the error rows
7. Check Airtable: `Processing Status` = `FAIL`

### Test with a broken submission (ERROR path)

1. Submit an Airtable record with no attachment
2. System should mark it ERROR within 60 seconds
3. Vendor gets an error notification email
4. Log shows the exception message

---

## Checking SQL Tables

Connect to SQL Server using SSMS.

After a submission is processed:

```sql
-- Check SubmissionRaw was loaded
SELECT COUNT(*) FROM dbo.SubmissionRaw;

-- Check SubmissionLog for grading result
SELECT TOP 10 * FROM dbo.SubmissionLog ORDER BY CreatedAt DESC;

-- Check QAResults for failure details
SELECT TOP 100 * FROM dbo.QAResults ORDER BY CreatedAt DESC;

-- Check SubmissionStage
SELECT TOP 10 * FROM dbo.SubmissionStage ORDER BY CreatedAt DESC;
```

---

## Dashboard and Metrics

### What is generated

After every processed submission, three CSV files and two HTML files are refreshed:

| File | Location | Description |
|---|---|---|
| `submission_history.csv` | `output/` | One row per submission. Master log. |
| `vendor_metrics.csv` | `output/` | One row per vendor. Aggregated metrics. |
| `processing_summary.csv` | `output/` | One row per day. Daily rollup. |
| `vendor_metrics.html` | `output/` | Color-coded vendor performance table. |
| `processing_summary.html` | `output/` | Daily submission breakdown table. |

### submission_history.csv columns

`submission_id`, `record_id`, `vendor_email`, `vendor_name`, `site_number`,
`attachment_filename`, `submitted_at`, `processed_at`, `status`, `score`,
`error_count`, `output_report_path`, `sql_project_key`, `execution_id`,
`archived_file_path`, `notes`

### vendor_metrics.csv columns

`vendor_email`, `vendor_name`, `total_submissions`, `total_pass`,
`total_fail`, `total_error`, `pass_rate_pct`, `fail_rate_pct`,
`avg_score_on_fail`, `latest_submission_at`, `avg_turnaround_seconds`

### processing_summary.csv columns

`date`, `total_submissions`, `total_pass`, `total_fail`, `total_error`,
`pass_rate_pct`, `unique_vendors`, `unique_sites`

### How to open the dashboards

The dashboard is served from a local HTTP server started by the launcher — just use the shortcut or the launcher script and your browser opens automatically.

Direct URL (once the server is running):
```
http://127.0.0.1:8765/executive_dashboard.html
```

The dashboard has three control buttons to **Start**, **Stop**, and **Rebuild** the pipeline without touching a terminal.

Row colors in `vendor_metrics.html`:
- Green = pass rate ≥ 95%
- Amber = pass rate 80–94%
- Red = pass rate < 80%

### How to export all survey history

The file `output/submission_history.csv` IS the complete exportable survey history.
Open it in Excel at any time. It accumulates across all runs permanently.

---

## Archive Schemas

### Submission Archive Record (`archive/submissions/YYYY/MM/DD/<id>_meta.json`)

```json
{
  "record_id": "recABC123456",
  "submission_id": "SUB-2025-001",
  "vendor_email": "vendor@acme.com",
  "vendor_name": "Acme Security",
  "site_number": "SITE-42",
  "attachment_filename": "acme_export_2025.xlsx",
  "archived_file_path": "C:/SiteOwlQA_App/archive/submissions/2025/05/01/recABC123456_acme_export_2025.xlsx",
  "submitted_at": "2025-05-01T08:30:00+00:00",
  "processed_at": "2025-05-01T09:01:49+00:00",
  "status": "PASS",
  "score": 98.5,
  "error_count": 0,
  "output_report_path": "",
  "sql_project_key": "SITE-42",
  "execution_id": "EX_20250501_090143_a3f2",
  "notes": ""
}
```

### Execution Archive (`archive/executions/<execution_id>.json`)

```json
{
  "execution_id": "EX_20250501_090143_a3f2",
  "submission_id": "SUB-2025-001",
  "record_id": "recABC123456",
  "vendor_email": "vendor@acme.com",
  "site_number": "SITE-42",
  "status": "PASS",
  "score": 98.5,
  "error_message": "",
  "rows_loaded": 42,
  "duration_seconds": 5.873,
  "executed_at": "2025-05-01T09:01:49.000000"
}
```

### Review Archive (`archive/reviews/<execution_id>_review.json`)

```json
{
  "status": "APPROVED_WITH_WARNINGS",
  "risk_level": "MEDIUM",
  "summary": "Pipeline ran successfully. Concurrency risk in SubmissionRaw staging remains.",
  "issues": [
    {
      "severity": "HIGH",
      "type": "Concurrency",
      "detail": "Global truncation of SubmissionRaw is unsafe if multiple records process simultaneously."
    }
  ],
  "recommended_fixes": [
    "Add SubmissionID-aware staging isolation.",
    "Centralize Airtable field mappings in config."
  ],
  "reviewed_at": "2025-05-01T09:01:49.000000",
  "execution_id": "EX_20250501_090143_a3f2"
}
```

### Lesson Archive (`archive/lessons/LESSON_NNN.json`)

```json
{
  "lesson_id": "LESSON_001",
  "task_category": "sql_import",
  "failed_pattern": "Trusted import wizard destination without verifying target table.",
  "root_cause": "Import wizard auto-created SQL_IMPORT_DB instead of loading ReferenceRaw.",
  "fix_pattern": "Always verify row count in destination table after import.",
  "generalized_rule": "Never assume import wizard respected the intended table. Verify row counts explicitly.",
  "confidence": 0.95,
  "tags": ["sql", "import", "wizard", "verification"],
  "created_at": "2025-05-01T09:01:49.000000"
}
```

---

## Known Risks and Reviewer Warnings

### ⚠️ CRITICAL: SubmissionRaw Concurrency Risk

**Problem**: The MVP uses `TRUNCATE TABLE dbo.SubmissionRaw` before each insert.
If two submissions are processed at the same time (e.g., two records returned in the same poll), the truncation of one will destroy the rows of the other.

**Current mitigation**: The polling loop processes records **sequentially** (one at a time). As long as `POLL_INTERVAL_SECONDS` is large enough that one submission finishes before the next poll, this is safe.

**MVP rule**: Do NOT process submissions in parallel threads. The loop is intentionally single-threaded.

**Production upgrade**:
```sql
-- Instead of TRUNCATE, use:
DELETE FROM dbo.SubmissionRaw WHERE SubmissionID = @SubmissionID;
-- Then INSERT with SubmissionID populated
-- Stored procedures must also filter by SubmissionID
```

### Other Reviewer Warnings

| Risk | Severity | Notes |
|---|---|---|
| Airtable token in .env | LOW | Never commit .env. Use Windows ACL to restrict file access. |
| No retry on Airtable 429 (rate limit) | LOW | Rare in practice at 60s poll intervals with low volume. |

---

## Recommended Next Production Upgrades

For active prioritization and status tracking of these upgrades, use [`development.md`](./development.md) as the source of truth.

1. **Streamlit dashboard** (optional) — a `streamlit run dashboard_app.py` app reading the CSVs live. Label clearly as optional.
2. **Windows Service** — use `pywin32` to register as a proper Windows Service instead of Task Scheduler. Cleaner restart behavior.
3. **Alerting on repeated vendor failures** — if a vendor has 3+ consecutive FAILs, send an internal alert email.
4. **Airtable webhook** (future) — replace polling with an Airtable webhook for sub-second response. Requires a reachable HTTP endpoint.

---

## Debugging Common Failures

### “EnvironmentError: Required environment variable X is missing”
→ Open `.env` and fill in the missing value.

### “Connection to BigQuery failed”
→ Check that `GOOGLE_APPLICATION_CREDENTIALS` points to a valid service account JSON. Check that the service account has BigQuery Data Viewer role on the dataset.

### “Record recXXX has no attachment in field SiteOwl Export File”
→ The Airtable field name in your base doesn't match `AIRTABLE_FIELDS.attachment` in `config.py`. Update `config.py` or rename the Airtable field.

### “Vendor file missing required column: Project ID”
→ The vendor file uses different column names. `file_processor.py` does case-insensitive matching and strips whitespace. If still failing, check the actual column name in the vendor file.

### “Processing Status not updating in Airtable”
→ Check that your Airtable token has `data.records:write` scope.

### “Archive file not appearing”
→ Check that `SUBMISSIONS_DIR` path exists and is writable. Check logs for `Failed to archive submission metadata`.

### Metrics CSVs not updating
→ Check `output/` folder exists and is writable. Check logs for `Metrics/dashboard refresh failed`.

---

## 24/7 Operation Confirmation Checklist

After rebooting the machine, confirm:

- [ ] Task Scheduler shows `SiteOwlQA Pipeline` with Status = `Running`
- [ ] `logs/siteowl_qa.log` has fresh log entries
- [ ] Log shows `Found 0 pending submission(s)` appearing every 60 seconds
- [ ] Submit a test record in Airtable and confirm it processes within 60 seconds
- [ ] Check vendor email inbox for result
- [ ] Check `output/submission_history.csv` for the new row
