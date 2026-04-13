# Clone and Run Guide (Coworker Onboarding)

This guide is the **single source of truth** for getting SiteOwlQA running from a fresh clone.

---

## 1) What this repo includes

You are getting:
- Main pipeline orchestrator (`src/siteowlqa/main.py`)
- Submission worker orchestrators (`src/siteowlqa/queue_worker.py`)
- Metrics/dashboard orchestrator (`src/siteowlqa/metrics_worker.py`)
- Correction orchestrator (`src/siteowlqa/correction_worker.py`)
- Full phase flow (ingest → grade → notify → archive → review → metrics/dashboard)
- Windows launchers and scheduler scripts (`ops/windows/`)

---

## 2) Prerequisites

### Required
- Windows machine
- Python 3.11+
- SQL Server ODBC driver (17+)
- Access to Airtable base
- Access to SQL Server DB used by SiteOwlQA

### Recommended
- Git
- VS Code

---

## 3) Clone and bootstrap

```bat
git clone https://github.com/maximtsitolovsky-wal/VUES---Validation-Utility-Engine-Survey.git
cd VUES---Validation-Utility-Engine-Survey

python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
```

> Launch scripts auto-detect `.venv\Scripts\python.exe`. If not found, they fall back to `python` on PATH.

---

## 4) Configure secrets and runtime settings

### 4.1 User secrets (required)
Run:

```bat
.venv\Scripts\python -m siteowlqa.setup_config
```

This creates:
`%USERPROFILE%\.siteowlqa\config.json`

Includes:
- SQL server/database/driver
- Airtable token/base/table
- Optional SMTP creds
- Optional LLM Gateway
- Optional reference workbook settings

### 4.2 Runtime non-secret settings (.env)

```bat
copy .env.example .env
```

Then edit `.env` (poll interval, workers, output dirs, correction paths, etc).

---

## 5) Run modes

## Foreground debug mode
```bat
ops\windows\run_siteowlqa.bat
```

## Background + dashboard mode
```bat
ops\windows\start_pipeline.bat
```

## Stop pipeline
```bat
ops\windows\stop_pipeline.bat
```

## Auto-start on machine boot (admin)
```bat
ops\windows\setup_scheduler.bat
```

---

## 6) Pipeline phases (what “all phases” means)

### Phase 1 — Intake and grading
1. Poll Airtable for unprocessed submissions
2. Mark record as `QUEUED`
3. Worker picks up record, marks `PROCESSING`
4. Download vendor file
5. Normalize schema + apply Site Number overwrite rule
6. Load reference data
7. Grade rows/fields
8. Build PASS/FAIL/ERROR payloads
9. Update Airtable status + score fields

### Phase 2 — Governance and analytics
10. Archive raw submission + metadata
11. Archive execution result JSON
12. Run review pass and archive review JSON
13. Refresh metrics CSVs
14. Refresh dashboard HTMLs
15. Extract memory/lessons for recurring failure patterns

### Phase 3 — Autonomous correction loop
16. Correction worker scans PASS records with high True Score criteria
17. Applies post-pass correction flow
18. Persists correction state (idempotent)

---

## 7) Orchestrators and workers (agents in app runtime)

- **Main orchestrator:** `siteowlqa.main.run_forever`
  - Poll loop, startup/shutdown, crash recovery
- **Submission workers:** `siteowlqa.queue_worker.SubmissionWorker`
  - Parallel record execution (queue consumers)
- **Metrics orchestrator:** `siteowlqa.metrics_worker.MetricsRefreshWorker`
  - Single-writer for CSV/HTML output (prevents write races)
- **Correction orchestrator:** `siteowlqa.correction_worker.CorrectionWorker`
  - Autonomous correction polling and post-pass workflow

---

## 8) Smoke test checklist

1. Start app in foreground (`run_siteowlqa.bat`)
2. Confirm log line: config loaded from `%USERPROFILE%\.siteowlqa\config.json`
3. Submit one known-good file in Airtable
4. Confirm status transitions: blank/NEW → QUEUED → PROCESSING → PASS/FAIL
5. Check artifacts:
   - `archive/` new JSON and raw file copy
   - `output/*.csv` refreshed
   - `output/*.html` refreshed

---

## 9) Common failures

- **User config missing**: run `python -m siteowlqa.setup_config`
- **Airtable auth error**: bad token/base/table in user config
- **SQL connection error**: bad server/db/ODBC or missing DB access
- **No dashboard update**: check `logs/` and metrics worker startup messages

---

## 10) Git hygiene for coworkers

Never commit:
- `.env`
- `%USERPROFILE%\.siteowlqa\config.json`
- output archives/logs with production data

Always run from repo root or use provided launch scripts.
