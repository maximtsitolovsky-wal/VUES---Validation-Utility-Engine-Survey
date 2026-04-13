# SiteOwlQA Automation Pipeline

> Automated vendor QA pipeline: Airtable → Python → SQL-backed reference lookup → SMTP email.
> Runs 24/7 on a Windows machine with zero cloud dependencies.

> Active roadmap, delivery notes, and commit workflow live in [`development.md`](./development.md).
>
> **Project Layout**: Modern Python monorepo with `src/siteowlqa/` package, `scripts/` for utilities, `docs/` for documentation, and `ops/windows/` for Windows automation.

---

## Architecture Overview

```
 Airtable Form
      ↓  (vendor submits XLSX/CSV via Airtable form)

 Python Polling Service  (poll every 60 seconds)
      ↓  download attachment
      ↓  normalize columns, overwrite Project ID ← Airtable Site Number
      ↓  fetch site-scoped reference rows from SQL Server
      ↓  compare canonical headers in Python
      ↓  derive PASS / FAIL / ERROR + score in Python
      ↓  send email (SMTP, Office 365)
      ↓  PATCH Airtable Processing Status (PASS / FAIL / ERROR)
      ↓  archive raw file → archive/submissions/YYYY/MM/DD/
      ↓  save execution + review JSON
      ↓  refresh vendor_metrics.csv + submission_history.csv
      ↓  refresh HTML dashboards
      ↓  extract lesson if failure
```

### Module Map

| File | Lines | Purpose |
|---|---|---|
| `main.py` | 126 | Entry point, poll loop, signal handling |
| `poll_airtable.py` | 354 | 15-step per-record orchestrator |
| `config.py` | 192 | ALL env var access — centralized |
| `models.py` | 260 | All domain types (AirtableRecord, SubmissionResult…) |
| `utils.py` | 105 | Logging setup, ID generation, safe file delete |
| `airtable_client.py` | 207 | Airtable REST API (fetch, download, status update) |
| `file_processor.py` | 159 | XLSX/CSV load, header normalization, ProjectID overwrite |
| `sql.py` | 90 | SQL connection + site-scoped reference fetch |
| `emailer.py` | 195 | PASS/FAIL/ERROR emails with CSV attachment |
| `reviewer.py` | 462 | Internal static code reviewer |
| `archive.py` | 259 | Append-only JSON archive + raw file storage |
| `memory.py` | 227 | Tag+keyword lesson retrieval |
| `metrics.py` | 264 | Compute metrics, export CSVs |
| `dashboard.py` | 212 | Generate HTML dashboards from CSVs |

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
├── main.py                  # entry point
├── poll_airtable.py         # per-record 15-step processor
├── config.py                # all env vars + constants
├── models.py                # domain types
├── utils.py                 # helpers
├── airtable_client.py       # Airtable REST API
├── file_processor.py        # XLSX/CSV parser
├── sql.py                   # SQL Server reference data access
├── emailer.py               # SMTP email sender
├── reviewer.py              # internal code reviewer
├── archive.py               # append-only archive
├── memory.py                # lesson retrieval
├── metrics.py               # compute + export CSV metrics
├── dashboard.py             # generate HTML dashboards
├── .env                     # secrets (never commit this)
├── .env.example             # template
├── requirements.txt
├── prompts/
├── logs/                    # rotating log files
├── temp/                    # downloaded attachments (auto-cleaned)
├── output/                  # CSV exports + HTML dashboards
└── archive/
    ├── submissions/           # YYYY/MM/DD/<id>_meta.json + raw file copy
    ├── executions/            # <execution_id>.json
    ├── reviews/               # <execution_id>_review.json
    ├── lessons/               # LESSON_NNN.json
    ├── prompts/               # prompt snapshots
    └── code/                  # code snapshots
```

---

## Quick Start Setup

> New teammate onboarding? Use **[`docs/clone-and-run.md`](./docs/clone-and-run.md)** for the complete clone/bootstrap/run guide (including orchestrators, workers, and all pipeline phases).


### 1. Install Dependencies

```bash
# Install Python 3.11+ from https://python.org
# Install ODBC Driver 17 for SQL Server (if not present)
# Then:

cd C:\SiteOwlQA_App
pip install -r requirements.txt
```

### 2. Create User Configuration

Run the interactive setup wizard:

```bash
python -m siteowlqa.setup_config
```

This will prompt you for:
- SQL Server connection details
- Airtable API token and base ID
- (Optional) SMTP server settings
- (Optional) LLM Gateway credentials
- (Optional) Reference data workbook path

**Your sensitive data is saved to** `~/.siteowlqa/config.json` (NOT in the repo).

### 3. Run the Pipeline

**On Windows (recommended):**
```bash
start_pipeline.bat
```
This opens the dashboard in your browser.

**Or directly:**
```bash
python main.py
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

Double-click one of these batch files:

| File | Purpose |
|------|----------|
| `start_pipeline.bat` | Start pipeline + open dashboard |
| `stop_pipeline.bat` | Stop the running pipeline |
| `run_siteowlqa.bat` | Foreground mode (for debugging) |

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
2025-05-01 09:01:47,444 | INFO     | emailer         | PASS email sent to vendor@example.com
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

### How to open the HTML dashboards

1. Navigate to `C:\SiteOwlQA_App\output\`
2. Double-click `vendor_metrics.html` — opens in your browser
3. Double-click `processing_summary.html` — opens in your browser

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
| TRUNCATE is global | HIGH | See above. Sequential loop mitigates in MVP. |
| Email fails silently | MEDIUM | Error is logged, Airtable is updated. Vendor does not get email if SMTP fails. |
| Airtable token in .env | LOW | Never commit .env. Use Windows ACL to restrict file access. |
| No retry on transient SQL errors | LOW | pyodbc raises immediately on SQL failure. Airtable is marked ERROR. |
| No retry on Airtable 429 (rate limit) | LOW | Rare in practice at 60s poll intervals with low volume. |

---

## Recommended Next Production Upgrades

For active prioritization and status tracking of these upgrades, use [`development.md`](./development.md) as the source of truth.

1. **SubmissionID-isolated staging** — DELETE by SubmissionID instead of TRUNCATE. Allows safe concurrent processing.
2. **Multi-threaded processing** — after #1 is done, use `concurrent.futures.ThreadPoolExecutor` to process multiple submissions in parallel.
3. **Retry logic** — add exponential backoff for transient SQL and SMTP failures.
4. **Streamlit dashboard** (optional) — a `streamlit run dashboard_app.py` app reading the CSVs live. Label clearly as optional.
5. **SQL metrics tables** — INSERT metrics into a `dbo.VendorMetrics` SQL table instead of only CSV files. Enables SSMS reporting.
6. **Windows Service** — use `pywin32` to register as a proper Windows Service instead of Task Scheduler. Cleaner restart behavior.
7. **Alerting on repeated vendor failures** — if a vendor has 3+ consecutive FAILs, send an internal alert email.
8. **Airtable webhook** (future) — replace polling with an Airtable webhook for sub-second response. Requires a reachable HTTP endpoint.

---

## Debugging Common Failures

### “EnvironmentError: Required environment variable X is missing”
→ Open `.env` and fill in the missing value.

### “Connection to SQL Server failed”
→ Check that SQL Server is running. Check `SQL_SERVER` value in `.env`. Make sure your Windows user has access.

### “Record recXXX has no attachment in field SiteOwl Export File”
→ The Airtable field name in your base doesn't match `AIRTABLE_FIELDS.attachment` in `config.py`. Update `config.py` or rename the Airtable field.

### “Vendor file missing required column: Project ID”
→ The vendor file uses different column names. `file_processor.py` does case-insensitive matching and strips whitespace. If still failing, check the actual column name in the vendor file.

### “SMTP authentication failed”
→ Check `SMTP_USER`, `SMTP_PASS`, and `SMTP_SERVER` in `.env`. For Office 365, app passwords may be required if MFA is enabled.

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
