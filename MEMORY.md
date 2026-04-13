# MEMORY.md — SiteOwlQA Settled Decisions & Context
# Last updated: 2026-04-13

> This is the authoritative decision log for the SiteOwlQA project.
> Code Puppy reads this at the start of every session.
> Code Puppy appends to this at the end of every session that contains a decision.
> Do not re-open closed decisions unless explicitly instructed.
> Roadmap / delivery tracking lives in `development.md` — not here.

---

## 🏗️ Settled Architecture (Closed — Do Not Re-Debate)

### 2026-03-27 — Monorepo Layout Established
- **Decision:** Migrated to `src/siteowlqa/` package layout. Root `main.py` is a backward-compat wrapper only.
- **Impact:** All imports use `siteowlqa.` package qualification. Scripts live in `scripts/`. Docs in `docs/`. Windows ops in `ops/windows/`.
- **Closed:** Yes.

### 2026-03-27 — Single-Process Architecture
- **Decision:** One Python process. No message queues. No Docker. No cloud dependencies.
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
| `emailer.py`       | All email sending                         |
| `reviewer.py`      | Internal static code/run review           |
| `archive.py`       | Append-only JSON archive + raw file store |
| `memory.py`        | Lesson retrieval (tag+keyword)            |
| `config.py`        | ALL environment variable access           |
| `models.py`        | All shared data types                     |
| `utils.py`         | Logging setup, ID gen, safe file ops      |
| `metrics.py`       | Compute metrics, export CSVs              |
| `dashboard.py`     | Generate HTML dashboards from CSVs        |

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

## 📧 Email / SMTP Architecture (Closed)

### 2026-03-27 — SMTP is Optional / Airtable-Delegated by Default
- **Decision:** `SMTP_ENABLED=false` by default. Python writes PASS/FAIL/ERROR back to Airtable `Processing Status`. An Airtable automation rule triggers vendor email independently. `emailer.py` is preserved but bypassed until `SMTP_ENABLED=true`.
- **Closed:** Yes.

---

## ⚠️ Known Risks & Status

| Risk ID  | Description                                       | Status              |
|----------|---------------------------------------------------|---------------------|
| RISK-001 | Cross-submission contamination via SQL procs      | ✅ RESOLVED — Python owns grading |
| RISK-002 | Project ID overwrite must remain authoritative    | 🔴 OPEN — needs stronger post-normalization verification |
| RISK-003 | Airtable attachment URLs expire                   | ✅ RESOLVED — `scripts/download_all_attachments.py` mirrors all attachments to OneDrive labelled by Site ID; run on-demand or schedule |

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
2. ✅ **RISK-003** — `scripts/download_all_attachments.py` mirrors all attachments to OneDrive (idempotent, labelled by Site ID).
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

### 2026-04-13 — RISK-003 Resolved: Attachment Mirror Script
- **Decision:** Created `scripts/download_all_attachments.py`. Fetches all 57 Airtable records, downloads every attachment via PowerShell (NTLM proxy), labels files `SITE_{site_number}__{submission_id}__{filename}`, saves to `C:\Users\vn59j7j\OneDrive - Walmart Inc\Documents\BaselinePrinter\VUE Submissions\ATTACHMENTS`. Fully idempotent (skips existing files). Supports `--dry-run`. Exit code 1 on any failure.
- **Impact:** RISK-003 closed. Attachments are now on OneDrive and survive Airtable CDN URL expiry. Run again after any new submission batch.
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
