# Development Roadmap

This file is the canonical development tracker for `SiteOwlQA_App`.

Use it to track roadmap items, active work, decisions, and commit discipline.
If any other markdown file is updated with project status, next steps, implementation notes, or process guidance, it must reference this file.

## Source of Truth Rules

- `development.md` is the single source of truth for roadmap and delivery status.
- `README.md` should describe the system and operational setup, then point here for active development tracking.
- Any future status, architecture, or planning markdown should link back to `development.md`.
- Avoid duplicating roadmap content across multiple markdown files. DRY matters. Markdown spaghetti is still spaghetti.

## Git / Version Control Workflow

For every change we make in this project:

1. Make the smallest reasonable change.
2. Review the impacted files.
3. Stage only the intended files.
4. Create a focused git commit with a clear message.
5. Push the commit to the configured Walmart Git remote.

### Commit Standard

- Commit after each completed change set.
- Keep commits scoped to one concern whenever possible.
- Prefer messages in this style:
  - `docs: add development roadmap and repo workflow`
  - `feat: add vendor dashboard filter`
  - `fix: correct score calculation for partial matches`
  - `refactor: split dashboard rendering helpers`
  - `test: add regression coverage for grading edge case`

### Staging Standard

- Stage only files related to the change.
- Do not accidentally commit generated outputs, logs, temp files, archives, or secrets.
- Before committing, check `git status` and verify the diff is clean and intentional.

## Roadmap

### Current Priorities

- [x] Establish repo hygiene and development workflow.
- [x] Confirm the correct minimal tracked file set for this repository.
- [x] Review current modified Python files and group them into safe, focused commits.
- [x] Identify generated vs source artifacts that should remain out of git.
- [ ] Add or improve tests around active grading and Airtable processing behavior.

### Backlog

- [ ] Audit project structure for monorepo readiness.
- [ ] Reduce oversized modules by splitting responsibilities where needed.
- [ ] Add clearer local development and release workflow documentation.
- [ ] Review dashboards and generated HTML ownership boundaries.

## Decisions Log

### 2026-03-28 (Repository Discipline Enforcement)

- Enhanced .gitignore to exclude script temp files and outputs (`*_output.txt`, `_*.txt`)
- Committed 4 focused changes in separate commits:
  - fix: import path correction
  - docs: gitignore improvements
  - feat: utility scripts addition
  - docs: airtable troubleshooting guide
- Verified documentation hierarchy compliance - all markdown files properly reference development.md
- Excluded from git: config test data, log outputs, temp files
- Applied clean staging discipline - only committed intended source artifacts

### 2026-03-27 (Repository Structure Refactor)

- Migrated to modern 2026 monorepo layout:
  - `src/siteowlqa/` - core application package
  - `scripts/` - one-off utility and maintenance scripts
  - `docs/` - markdown documentation and requirements
  - `ops/windows/` - Windows-specific deployment and automation
  - `sql_migrations/` - SQL schema migrations (unchanged)
  - `prompts/` - LLM prompt templates (unchanged)
  - `tests/` - test suite (unchanged)
  - `tools/` - dashboard/reporting build tools (unchanged)
  - `pyproject.toml` - modern Python package metadata
- Updated all imports to use `siteowlqa.` package qualification
- Created root `main.py` wrapper for backward compatibility
- Established rule: commit each completed change set to Walmart Git.
- Existing markdown files should point to this document when they mention project evolution, status, or next steps.

## Windows Operations

For Windows users, batch launcher scripts are available in `ops/windows/`:

### Quick Start
- **Daily use:** Double-click `start_pipeline.bat`
- **24/7 automatic:** Run `setup_scheduler.bat` as admin (once)
- **Testing:** Use `run_siteowlqa.bat` for foreground/console output
- **Stop:** Run `stop_pipeline.bat`

See `ops/windows/README.md` for full documentation.

## Working Notes

Use this section to append short dated notes as we go.

- 2026-03-30 (DB Reload): Added `scripts/reload_reference_from_power_query.py` (Power Query COM approach — superseded same day).
- 2026-03-30 (DB Reload v2): Added `scripts/reload_reference_from_two_sheets.py` — final approach. Reads `CDFD1 P1` then `CDFD1 P2` from `Camera&Alarm Ref Data.xlsx` (OneDrive/Documents/BaselinePrinter/Excel), appends them (~1.8M rows, 58 cols), normalizes via existing `normalize_reference_dataframe()` pipeline, and bulk-inserts into `dbo.ReferenceRaw` + `dbo.ReferenceExport`. Uses calamine engine for fast reads. All grading logic unchanged. `SelectedSiteID` -> `ProjectID` mapping preserved.

- 2026-03-27 (Structure): Migrated to modern Python monorepo layout (src/siteowlqa)
- 2026-03-27 (Automation): Added Windows batch launchers for manual and scheduled operation
- 2026-03-28 (Governance): Enforced repository discipline and staging hygiene
  - Fixed import path for weekly_highlights module (dashboard_exec.py)
  - Added .gitignore rules for script temp files and outputs
  - Organized 6 new utility scripts in focused commits
  - Added airtable field mismatch troubleshooting documentation
  - Confirmed documentation hierarchy compliance (all docs reference development.md)
  - Applied clean staging discipline - excluded temp files, outputs, and config test data
