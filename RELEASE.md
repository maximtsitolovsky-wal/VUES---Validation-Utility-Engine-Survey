# SiteOwlQA Release Notes

---

## v1.3.0 — 2026-04-14

### What's in this release

Launcher and dashboard control buttons fully fixed. Startup is now one click.

---

### How to upgrade

```bat
git pull
.venv\Scripts\python -m pip install -r requirements.txt
```

Then restart via the Desktop shortcut or:
```powershell
powershell -ExecutionPolicy Bypass -File ops\windows\launch_siteowlqa_dashboard.ps1
```

> **No config changes required.** No DB migrations.

---

### What changed in v1.3.0

| Area | Change |
|---|---|
| **Launcher shortcut** | Desktop shortcut now reliably targets `launch_siteowlqa_dashboard.ps1` via PowerShell |
| **Dashboard buttons** | Start / Stop / Rebuild buttons now correctly report `running: true/false` after acting |
| **Process detection** | Fixed PowerShell `-like` pattern escaping — `*\main.py*` was double-escaped, always returned `false` |
| **Button response time** | Replaced blocking `subprocess.run(timeout=20)` with `Popen + sleep(2)` — buttons now respond in ~3s instead of timing out |
| **Stale server guard** | Multiple dashboard server instances no longer accumulate across restarts |

---

## v1.2.0 — 2026-04-14

### What's in this release

Full parallel Python grading pipeline with autonomous post-pass correction,
async queue architecture, and a hosted executive dashboard.

---

### How to deploy this release

#### Fresh install (new machine)

```bat
REM 1. Clone the repo
git clone https://github.com/maximtsitolovsky-wal/VUES---Validation-Utility-Engine-Survey.git
cd VUES---Validation-Utility-Engine-Survey

REM 2. Create the virtual environment
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt

REM 3. Run the interactive secrets wizard
REM  → creates %USERPROFILE%\.siteowlqa\config.json (never committed)
.venv\Scripts\python -m siteowlqa.setup_config

REM 4. Launch (opens browser automatically)
powershell -ExecutionPolicy Bypass -File ops\windows\launch_siteowlqa_dashboard.ps1
```

> Or double-click the **SiteOwlQA Launcher** Desktop shortcut after first run.

#### Upgrade from a previous version

```bat
git pull
.venv\Scripts\python -m pip install -r requirements.txt
```

Then restart via the Desktop shortcut or the launcher script above.

> **No DB migrations required** for this release.

#### Register auto-start (24/7 operation)

Right-click and **Run as Administrator**:
```
ops\windows\setup_scheduler.bat
```

This registers a Windows Task Scheduler task that starts the pipeline at every
system boot, even when no user is logged in.

---

### Prerequisites

| Requirement | Version |
|---|---|
| Windows | 10 / 11 / Server 2019+ |
| Python | 3.11 or 3.12 |
| ODBC Driver for SQL Server | 17 or 18 |
| SQL Server | Any version with `dbo.ReferenceExport` view |
| Airtable token scope | `data.records:read` + `data.records:write` |

---

### What changed in v1.2.0

| Area | Change |
|---|---|
| **Architecture** | Async queue model — poll thread enqueues, workers grade in parallel |
| **Workers** | Configurable `WORKER_THREADS` (default: 3) via `.env` |
| **Crash recovery** | On startup, resets `QUEUED`/`PROCESSING` records so they re-queue cleanly |
| **Dashboard** | Hosted on `localhost:8765` (no stale file:// snapshots) |
| **Post-pass correction** | Autonomous `CorrectionWorker` backfills PASS records with True Score ≥ 95 |
| **Reference data** | Background pre-warm thread — no cold-start delay on first submission |
| **Metrics** | Single-writer `MetricsRefreshWorker` prevents CSV write races |
| **Launchers** | All launchers use relative paths — works on any clone location |
| **Email** | SMTP removed — Airtable automation owns all vendor email delivery |

---

### Known limitations

| Issue | Severity | Workaround |
|---|---|---|
| `SubmissionRaw` global truncation | HIGH | Workers process sequentially by default; do not set `WORKER_THREADS > 1` until SQL migration 08+ is applied |
| No retry on Airtable 429 | LOW | Rare at 60-second poll intervals |
| No retry on transient SQL errors | LOW | Record is marked `ERROR`; re-submit via Airtable |

See `README.md → Known Risks` for full details.

---

### File layout (quick ref)

```
main.py                       ← run this (or use a launcher)
src/siteowlqa/                ← application package
ops/windows/                  ← Windows launchers
  start_pipeline.bat          ← daily use
  stop_pipeline.bat
  run_siteowlqa.bat           ← foreground / debug
  setup_scheduler.bat         ← auto-start (admin)
docs/clone-and-run.md         ← teammate onboarding guide
.env.example                  ← copy → .env and edit
```

---

### Where logs live

| Log | Path |
|---|---|
| stdout | `logs\siteowlqa.stdout.log` |
| stderr | `logs\siteowlqa.stderr.log` |

Logs rotate at 10 MB, keeping 5 backups.

---

### Support

- Primary docs: [`README.md`](./README.md)
- Onboarding: [`docs/clone-and-run.md`](./docs/clone-and-run.md)
- Ops scripts: [`ops/windows/README.md`](./ops/windows/README.md)
- Config reference: [`docs/configuration.md`](./docs/configuration.md)
