### 2026-04-23 — BigQuery-with-Fallback Reference Source Added
- **Decision:** Added `bigquery_with_fallback` as a new reference source mode. When BQ is the bottleneck (slow, down, quota errors), the pipeline now auto-falls back to the local Excel workbook. Keeps grading running even when BQ is flaky. Excel workbook now serves as a local backup cache for reference data.
- **Impact:** `src/siteowlqa/reference_data.py` (new `_fetch_with_bq_fallback()` function, updated `_resolve_reference_source()`), `.env.example` (documented new mode), `tests/test_reference_data.py` (added `BigQueryFallbackTests` class with 5 tests).
- **Config:** Set `REFERENCE_SOURCE=bigquery_with_fallback` and ensure `REFERENCE_WORKBOOK_PATH` points to a valid Excel backup.
- **Closed:** Yes.

### 2026-04-17 — Vendor Assignment Tracker Built & Shipped
- **Decision:** Built complete vendor assignment tracking system. Reads vendor assignments from Excel file (`Vendor ASSIGN. 4.2.26.xlsx`, one sheet per vendor), compares against Scout Airtable completions, calculates remaining assignments + completion rates + velocity. Dashboard displays color-coded pills (green ≥80%, yellow ≥50%, red <50%). All 5 vendors tracked: Wachter, Techwise, SAS, Everon, CEI. Multi-sheet Excel loader reads ALL sheets automatically, uses sheet name as vendor name. Data integrated into `team_dashboard_data.json`, rendered in Scout section of executive dashboard.
- **Impact:** `src/siteowlqa/vendor_assignment_tracker.py` (new, 350 lines), `src/siteowlqa/team_dashboard_data.py` (vendor payload builder), `src/siteowlqa/dashboard_exec.py` (renderVendorAssignmentPills() + UI pills), `test_vendor_tracking.py` (new), `docs/vendor-assignment-tracking.md` (created earlier).
- **Test Results:** 758 total assignments loaded from 5 sheets, 263 completed submissions matched, 495 remaining. CEI leading with 234 completions (68%), SAS nearly done (7/8).
- **Closed:** Yes.

### 2026-04-15 — Scout Image Sync Integrated Into Main Pipeline
- **Decision:** Scout image downloader now runs as `ScoutSyncWorker` daemon thread inside `main.py` alongside `CorrectionWorker` and `MetricsRefreshWorker`. 60s startup delay, then every 6h while pipeline is running. Uses PowerShell `Invoke-WebRequest` (WinINet/browser stack) for CDN downloads — only path that reaches `v5.airtableusercontent.com` on Walmart network (DNS blocked at WinSock level, see RISK-003). Standalone `scripts/scout_downloader.py` + scheduled tasks (Mon-Fri 10AM/3PM) remain registered as redundancy layer.
- **Impact:** `src/siteowlqa/scout_sync_worker.py` (new), `src/siteowlqa/main.py`, `MEMORY.md`.
- **Closed:** Yes.

### 2026-04-15 — RISK-003 CDN fix: `v5.airtableusercontent.com` is DNS-blocked for Python `requests` on Walmart network. Use `subprocess` + PowerShell `Invoke-WebRequest` (WinINet/browser stack) for image downloads. Confirmed 1.3MB image downloaded successfully via this path. `scripts/scout_downloader.py` rebuilt to use this method.
- **Decision:** Python `requests` library CANNOT reach `v5.airtableusercontent.com` — DNS blocked at WinSock level. PowerShell `Invoke-WebRequest` uses WinINet (same as browsers) which accesses PAC/auto-proxy and CAN reach CDN. All image downloads now go through PowerShell subprocess. API record fetching stays in `requests` (works fine for `api.airtable.com`).
- **Impact:** `scripts/scout_downloader.py`, `ops/windows/run_scout_downloader.bat`, `ops/windows/ScoutDownloader_Task.xml`, `ops/windows/register_scout_task.ps1`, `MEMORY.md`.
- **Closed:** Yes.
# MEMORY.md — VUES Settled Decisions & Context
# Last updated: 2026-04-15

> This is the authoritative decision log for the VUES project.
> Code Puppy reads this at the start of every session.
> Code Puppy appends to this at the end of every session that contains a decision.
> Do not re-open closed decisions unless explicitly instructed.
> Roadmap / delivery tracking lives in `development.md` — not here.

---

## ⚡ QUICK REF — Read This First, Read It Fast

> You must be able to answer these from memory before touching a file.
> If you can't, you skipped this section. Go back.

### Stack (Never Re-Derive)
| Key | Value |
|-----|-------|
| Language | Python 3.x, single-process, no Docker |
| Platform | Windows, Task Scheduler, no cloud deps |
| DB | SQL Server via `sql.py` — reference rows only |
| External | Airtable API (polled every 60s). Email via Airtable automations — no SMTP in codebase. |
| UI | `ui/executive_dashboard.html` → `output/` → `served_dashboard/` |
| Credentials | `~/.siteowlqa/config.json` — NOT `.env` |

### Module Ownership (One-Liner Each)
| Module | Owns — nothing else |
|---|---|
| `config.py` | **ALL** `os.getenv` calls. Zero exceptions. |
| `sql.py` | SQL connection + site-scoped reference rows |
| `models.py` | All shared data types |
| `poll_airtable.py` | Per-record 15-step orchestration |
| `airtable_client.py` | All Airtable API calls |
| `file_processor.py` | XLSX/CSV load + header normalisation |
| `emailer.py` | Deleted. Airtable automation handles all vendor email. |
| `archive.py` | Append-only JSON store. **Never delete.** |
| `memory.py` | Lesson retrieval (tag + keyword) |
| `metrics.py` | Compute metrics, export CSVs |
| `dashboard.py` | Generate HTML from template + CSVs |
| `dashboard_exec.py` | Inject data into `ui/executive_dashboard.html` template |
| `reviewer.py` | Internal static code/run review |
| `main.py` | Entry point, poll loop, signal handling only |

### Non-Negotiable Rules
- `config.py` is the **only** caller of `os.getenv`. Anywhere else = bug.
- Archive is **append-only**. No deletes, ever.
- Poll loop **never crashes** — catch at record level, not loop level.
- Files ≤ 600 lines. Split on cohesion, not line count.
- Commit after every completed change. Small + scoped.
- Never force-push.
- `ui/executive_dashboard.html` is the source template. Edit it, not `output/` or `served_dashboard/` directly (except for emergency sync patches).

### Open Risks (Check Before Touching These Areas)
| Risk | Area | Status |
|---|---|---|
| RISK-002 | Project ID overwrite post-normalisation | 🔴 OPEN |
| RISK-003 | Airtable attachment URL expiry / no monitoring | 🔴 OPEN |

### Last 3 Decisions (Newest First)
1. **2026-04-23** — BigQuery-with-Fallback: Added `bigquery_with_fallback` reference source. BQ is primary; Excel workbook is automatic backup when BQ fails. Keeps grading pipeline running through BQ outages.
2. **2026-04-17** — Vendor Assignment Tracker: Built complete vendor assignment tracking vs Scout completions. 5 vendors tracked with color-coded completion pills.
3. **2026-04-15** — Scout Image Sync integrated into main pipeline as daemon thread. Uses PowerShell subprocess for CDN downloads (RISK-003 workaround).

---

## 🏗️ Settled Architecture (Closed — Do Not Re-Debate)

### 2026-03-27 — Monorepo Layout Established
- **Decision:** Migrated to `src/siteowlqa/` package layout. Root `main.py` is a backward-compat wrapper only.
- **Impact:** All imports use `siteowlqa.` package qualification. Scripts live in `scripts/`. Docs in `docs/`. Windows ops in `ops/windows/`.
- **Closed:** Yes.

### 2026-03-27 — Single-Process Architecture
- **Decision:** One Python process. No message queues. No cloud dependencies.
- **Docker (2026-04-14):** Docker Desktop installed (Hyper-V backend, `WslEngineEnabled:false`). Dev hot-reload via `docker compose watch` + `watchmedo`. `Dockerfile`, `docker-compose.yml`, `.dockerignore` committed. Dashboard exposed on port 8765. User config mounted read-only from `%USERPROFILE%/.siteowlqa/`.
- **Rationale:** Target environment is a Windows machine with no infrastructure budget. Simplicity beats scalability here.
- **Closed:** Yes.

### 2026-03-27 — Polling over Webhooks
- **Decision:** Poll Airtable every 60 seconds. Webhooks not used (Airtable webhook action not available at time of decision).
- **Closed:** Yes.

### 2026-03-27 — Python Owns Grading Logic (RISK-001 Resolved)
- **Decision:** Python is the source of truth for grading. SQL Server supplies site-scoped reference rows only.
- **Rationale:** Eliminated cross-submission contamination risk that existed when grading lived in SQL procs.
- **Closed:** Yes.

### 2026-03-27 — Module Ownership Hard Boundaries
- **Decision:** Each module owns one concern. These are hard boundaries.

| Module             | Owns                                      |
|--------------------|-------------------------------------------|
| `main.py`          | Entry point, poll loop, signal handling   |
| `poll_airtable.py` | Per-record 15-step orchestration          |
| `airtable_client.py` | All Airtable API calls                  |
| `file_processor.py`| XLSX/CSV load and header normalization    |
| `sql.py`           | SQL connection + site-scoped ref rows     |
| `emailer.py`       | Deleted — Airtable automation handles email       |
| `reviewer.py`      | Internal static code/run review           |
| `archive.py`       | Append-only JSON archive + raw file store |
| `memory.py`        | Lesson retrieval (tag+keyword)            |
| `config.py`        | ALL environment variable access           |
| `models.py`        | All shared data types                     |
| `utils.py`         | Logging setup, ID gen, safe file ops      |
| `metrics.py`       | Compute metrics, export CSVs              |
| `dashboard.py`     | Generate HTML dashboards from CSVs        |
| `scout_sync_worker.py` | Scout image downloader daemon thread   |
| `vendor_assignment_tracker.py` | Vendor assignment tracking vs Scout completions |

- **Closed:** Yes.

### 2026-03-27 — Config Centralisation
- **Decision:** `config.py` is the only module that calls `os.getenv`. No exceptions.
- **Closed:** Yes.

### 2026-03-27 — Archive is Append-Only
- **Decision:** `archive.py` never deletes lessons or execution records. Append only.
- **Closed:** Yes.

### 2026-03-27 — Main Loop Never Crashes
- **Decision:** Catch exceptions at the per-record level, not at the poll loop level.
- **Closed:** Yes.

---

## 📧 Email Architecture

### 2026-04-13 — SMTP Removed, Airtable Automation Handles All Email
- **Decision:** `emailer.py` deleted. No SMTP code in codebase. Pipeline writes PASS/FAIL/ERROR to Airtable `Processing Status`; an Airtable automation rule watches that field and sends vendor email independently.
- **Closed:** Yes.

---

## ⚠️ Known Risks & Status

| Risk ID  | Description                                       | Status              |
|----------|---------------------------------------------------|---------------------|
| RISK-001 | Cross-submission contamination via SQL procs      | ✅ RESOLVED — Python owns grading |
| RISK-002 | Project ID overwrite must remain authoritative    | 🔴 OPEN — needs stronger post-normalization verification |
| RISK-003 | Airtable attachment URLs expire                   | 🔴 OPEN — no uptime monitoring yet |

---

## 📦 Reference Data Pipeline (Closed)

### 2026-03-30 — Two-Sheet Reference Load (Final Approach)
- **Decision:** `scripts/reload_reference_from_two_sheets.py` is the canonical way to reload reference data. Reads `CDFD1 P1` then `CDFD1 P2` from `Camera&Alarm Ref Data.xlsx` (OneDrive/Documents/BaselinePrinter/Excel), appends (~1.8M rows, 58 cols), normalizes via `normalize_reference_dataframe()`, bulk-inserts into `dbo.ReferenceRaw` + `dbo.ReferenceExport`.
- **Supersedes:** `scripts/reload_reference_from_power_query.py` (Power Query COM approach — abandoned same day).
- **Engine:** calamine (fast reads).
- **`SelectedSiteID` → `ProjectID` mapping:** preserved.
- **Closed:** Yes.

---

## 🗂️ Repository Hygiene (Closed)

### 2026-03-28 — Gitignore Extensions
- **Decision:** `.gitignore` excludes: `*_output.txt`, `_*.txt`, logs, temp files, config test data.
- **Closed:** Yes.

### 2026-03-28 — Staging Discipline
- **Decision:** Stage only files related to the change. Check `git status` + diff before every commit. Never commit generated outputs, logs, temp files, archives, or secrets.
- **Closed:** Yes.

### 2026-03-28 — Commit Message Format
- **Convention:** `type: short description` — types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.
- **Closed:** Yes.

---

## 🔮 Open Upgrade Paths (Prioritised)

1. ⬜ **RISK-002** — Stronger post-normalization Project ID verification.
2. ⬜ **RISK-003** — Uptime monitoring / heartbeat for Airtable attachment URL expiry.
3. ⬜ Upgrade `memory.py` lesson retrieval to semantic search when lessons > 100.
4. ⬜ Consider Windows Service wrapper instead of Task Scheduler.
5. ⬜ Audit project structure for monorepo readiness (deeper split if needed).
6. ⬜ Improve E2E test coverage around grading and Airtable processing.

---

## 📝 Session Log

> Append new entries here. Format:
> ### YYYY-MM-DD — <short title>
> - **Decision:** ...
> - **Impact:** ...
> - **Closed:** Yes / No

### 2026-04-14 — Relentless Memory Agent System Built
- **Decision:** Built a full memory agent system for SiteOwlQA: 5 spec files in `docs/memory-agent/` (AGENT.md, MEMORY_POLICY.md, MEMORY_SCHEMA.md, HANDOFF_SPEC.md, MEMORY_BACKEND_SPEC.md). Backend is file-only: `MEMORY.md` as human-readable canonical + `durable.jsonl` as machine-searchable index. Session notes per day. Handoff blocks at session close. Registered as `SKILL_RELENTLESS_MEMORY` in `skills/`. Store seeded with 3 bootstrap records (MEM-20260414-001/002/003).
- **Impact:** `docs/memory-agent/` (5 new files + store/ dir structure), `skills/SKILL_RELENTLESS_MEMORY.md`, `skills/INDEX.md`, `INFRA.md` (created same session).
- **Rule:** Load `docs/memory-agent/store/handoff_index.md` at session start if continuing prior complex work. Token budget: ≤5 records, ≤800 tokens. Never dump full MEMORY.md into context.
- **Closed:** Yes.

### 2026-04-13 — Git Truth Guard Added
- **Decision:** Added a dedicated git-verification layer: `tools/git_truth_guard.py`, `skills/SKILL_GIT_TRUTH_GUARD.md`, `prompts/git_truth_guard_prompt.md`, and `docs/git-truth-orchestration.md`. Completion claims now require proof that local HEAD equals the authoritative remote branch HEAD, not just a claimed push.
- **Impact:** `development.md` now defines receipt-based completion. `skills/INDEX.md` includes the Git Truth Guard skill. Future multi-agent orchestration must separate implementation from git publication verification.
- **Closed:** Yes.

### 2026-04-13 — Meta-Skill Added (Self-Creating Loop Closed)
- **Decision:** Added `SKILL_SKILL_EXTRACTION.md` — the meta-skill that teaches Code Puppy how to extract skills from any completed task. Defines the Skill vs Decision vs One-off distinction, naming convention, minimum viable skill, and when NOT to extract. This closes the self-creation loop: every session now has an explicit playbook for generating its own playbooks.
- **Impact:** `skills/INDEX.md` updated. `SKILL_GOVERNANCE_SETUP.md` should reference this skill on future projects.
- **Closed:** Yes.

### 2026-04-13 — Skill Framework Established
- **Decision:** Created `skills/` directory with `INDEX.md` + 4 seed skills: GOVERNANCE_SETUP, FLAT_HTML_REPORT, GIT_FOCUSED_COMMIT, ORCHESTRATION_MAP. Code Puppy is now mandated to check `skills/INDEX.md` before every task and extract a skill after any repeatable task. This is the mechanism for moving from repetition to autonomy.
- **Impact:** `CLAUDE.md` updated with SKILL PROTOCOL (Step 1b + Step 4). All future sessions gain accumulated playbooks.
- **Closed:** Yes.

### 2026-04-13 — Orchestration Map Created
- **Decision:** Created `orchestration_map.html` — a self-contained visual of the 15-step pipeline, module boundaries, learning loop, and decision protocol. Lives in project root. Not served — open directly in browser.
- **Impact:** No code changes. Documentation artifact only.
- **Closed:** Yes.

### 2026-04-13 — Governance Layer Established
- **Decision:** Created `CLAUDE.md` (Code Puppy governance constitution) and `MEMORY.md` (this file). Code Puppy is mandated to read MEMORY.md before every task and update it after every decision. Goal: less thinking, more execution.
- **Impact:** All future Code Puppy sessions are governed by this protocol. No new decisions should re-derive what is already in this file.
- **Closed:** Yes.

### 2026-04-13 — Airtable Credentials (Both Sources Confirmed Live)
- **Decision:** Scout credentials moved from `.env` SCOUT_* vars (wiped on every reset) into `~/.siteowlqa/config.json` permanently. This is the authoritative credential store — never `.env`.
- **Survey:** base=`apptK6zNN0Hf3OuoJ` | table=`Submissions` | token=`pattXz7pnoAIRQ89q...` (full in config.json)
- **Scout:**  base=`appAwgaX89x0JxG3Z` | table=`Submissions` | token=`patPR0WWxXCE0loRO...` (full in config.json)
- **Smoke test:** ALL CHECKS PASSED — both Airtable sources 200 OK.
- **Impact:** `user_config.py`, `config.py`, `setup_config.py`, `.env.example` updated.
- **Closed:** Yes.

### 2026-04-13 — Governance Hardened (QUICK REF + Proof-of-Read Mandate)
- **Decision:** Added `QUICK REF` block to top of MEMORY.md (stack, module ownership, rules, open risks, last 3 decisions in one scan). Updated CLAUDE.md Step 1 to require an explicit `MEMORY CHECK` statement before any file operation. Less thinking, more decisions is now structurally enforced, not aspirational.
- **Impact:** `CLAUDE.md`, `MEMORY.md`. No code changes.
- **Closed:** Yes.

### 2026-04-13 — Orchestration Map Bugs Fixed + 82-Check Audit Suite Added
- **Decision:** `function tick(){}` declaration was eaten during guide-panel injection — restored via `replace_in_file`. HUD edge count hardcoded as 25, actual array is 27 — corrected. `served_dashboard/` files missing Architecture + Admin nav links (stale copy of generated HTML) — synced directly. Root cause of silent patch failures: large-file `write_text()` in inline scripts silently drops on Windows; use `replace_in_file` tool instead.
- **Impact:** `orchestration_map.html`, `served_dashboard/executive_dashboard.html`, `served_dashboard/executive_dashboard_puppy_inline.html`, `_audit_final.py`.
- **Rule added:** When patching large generated HTML files, always use `replace_in_file` tool — never `Path.write_text()` from an inline script.
- **Closed:** Yes.

### 2026-04-13 — Deep Architecture Map + Dashboard Sync Fix
- **Problem:** Architecture tab was too shallow (7 nodes, no real module detail). Dashboard `served_dashboard/` was 60KB stale — Scout + vendorHeatmap present in `output/` but not synced.
- **Dashboard fix:** Ran `tools/publish_served_dashboard.py`. Nav link (Architecture) preserved because `output/executive_dashboard.html` already had it. `served_dashboard/` now 308KB, matches `output/`.
- **Architecture decision:** Read `main.py`, `poll_airtable.py`, `python_grader.py`, `metrics_worker.py`, `archive.py` directly before designing. 59 real nodes across 8 realms: root (8), pipeline (8), grader (7), async_workers (8), datastore (7), airtable (8), correction (7), output (6).
- **Key nodes:** `status_from_score()` single decision function, `CorrectionStateDB` SQLite dedup, `COMPARABLE_COLUMNS` canonical header set, `GradingInconsistencyError`, `Decimal(str(...))` float stability, RISK-003 CDN+OneDrive, ghost-data-prevention rule, 14-step process_record() orchestrator, mark_dirty() dirty-flag pattern, append-only archive with 6 subdirs.
- **File:** `orchestration_map.html` — 512 lines, 22/22 checks. Opens from `ui/executive_dashboard.html` via Architecture nav link.
- **Rule reconfirmed:** NEVER skim modules before building architecture. Read the actual source code first.
- **Closed:** Yes.
