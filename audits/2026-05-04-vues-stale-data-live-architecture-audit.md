# VUES Live Data Architecture Audit
- **Audit ID:** integrity-marshal-9e98ec-20260504-0945
- **Auditor:** Integrity Marshal (integrity-marshal-9e98ec)
- **Audit Time:** 2026-05-04T09:45:04Z
- **Requested By:** Maxim (project owner)
- **Target:** VUES Dashboard — Live Data Compliance & Architecture Integrity
- **Scope:** MEMORY.md, ui/*.html, ui/team_dashboard_data.json, src/siteowlqa/team_dashboard_data.py, src/siteowlqa/metrics_worker.py, tools/vues_preview_auto_sync.py, tools/serve_dashboard.py, tools/run_dashboard_server.py, relayops/tasks/open/*, relayops/state/, docs/LIVE_DASHBOARD_GUIDE.md, docs/vues_truly_live_architecture.md, audits/2026-04-28-*.md

---

## Evidence Gathered This Run

| Source | Verified |
|--------|----------|
| MEMORY.md (full read) | ✅ |
| src/siteowlqa/team_dashboard_data.py | ✅ |
| src/siteowlqa/metrics_worker.py | ✅ |
| src/siteowlqa/local_dashboard_server.py | ✅ |
| tools/run_dashboard_server.py (first 80 lines) | ✅ |
| tools/serve_dashboard.py (first 80 lines) | ✅ |
| tools/vues_preview_auto_sync.py (full read) | ✅ |
| docs/LIVE_DASHBOARD_GUIDE.md | ✅ |
| docs/vues_truly_live_architecture.md | ✅ |
| relayops/state/memory-vues-truly-live.md | ✅ |
| relayops/tasks/open/TASK-20260427-scout-stale-data-blocker.md | ✅ |
| relayops/tasks/open/TASK-20260427-scout-html-live-data.md | ✅ |
| audits/2026-04-28-vues-viewer-data-integrity-audit.md | ✅ |
| ui/ file sizes (via list_files) | ✅ |
| grep: fetch/loadData/BAKED in ui/*.html | ✅ |
| Airtable live count (696 vs 701 claim) | ❌ UNVERIFIABLE — no Airtable API access during this run |

---

```
═══════════════════════════════════════════════════════════════
                    INTEGRITY AUDIT REPORT
═══════════════════════════════════════════════════════════════

📋 VERDICT: FAIL
⚠️  SEVERITY: BLOCKER

───────────────────────────────────────────────────────────────
                         FINDINGS
───────────────────────────────────────────────────────────────

| # | Category               | Finding                                                                                             | Severity |
|---|------------------------|-----------------------------------------------------------------------------------------------------|----------|
| F-001 | Stale UI Files (SIZE) | ui/*.html files are 7.8MB each. LIVE_DASHBOARD_GUIDE.md explicitly states clean templates must be ~17KB. These are BAKED files containing embedded static JSON data — the same root cause flagged as BLOCKER in the 2026-04-28 audit. NOT FIXED. | BLOCKER |
| F-002 | Stale JSON in Git      | ui/team_dashboard_data.json is 9.3MB — a static snapshot committed to git and served as though current. Users hitting this file will always see stale data unless a live pipeline is running and auto-pushing. | BLOCKER |
| F-003 | Prior Repair Orders Never Resolved | RO-003 (scout stale data) and RO-004 (no fetch() calls in scout.html) were issued in the 2026-04-28 BLOCKER audit. Both remain in open/ tasks (TASK-20260427-scout-stale-data-blocker, TASK-20260427-scout-html-live-data). No evidence of resolution in any file read this run. | BLOCKER |
| F-004 | Truly Live Setup Checklist: All Items UNCHECKED | relayops/state/memory-vues-truly-live.md contains a 7-item setup checklist (4 terminals + 3 verify steps). Every single item is unchecked [ ]. This is the required operational setup for live data. It has NEVER been confirmed as running. | BLOCKER |
| F-005 | Hardcoded Stale Count in Auto-Sync Script | tools/vues_preview_auto_sync.py lines 57-61 contain hardcoded count checks: `if '"total_submissions":372' in content` and `elif '"total_submissions":369' in content`. Current reported count is ~696-701. This script is months stale and would NEVER log the correct count or detect sync success. | HIGH |
| F-006 | Wrong Serving Path (Root Cause of User Complaint) | Architecture mandates: `output/` = live server path (MetricsRefreshWorker → localhost HTTP). `ui/` = git distribution snapshot, NOT for live monitoring (explicitly stated in LIVE_DASHBOARD_GUIDE.md). If the user is seeing stale data, they are loading from `ui/` — either via file:// URL or from a server pointed at `ui/` instead of `output/`. | BLOCKER |
| F-007 | 696 vs 701 Count Discrepancy | User reports dashboard shows 696 records vs Airtable's 701. This is plausible given F-001/F-002 (baked data). However, the authoritative Airtable count cannot be independently verified in this audit run. Labeled: user-reported, unverifiable from this run. | HIGH |
| F-008 | Escalating Stale Count Pattern | Historical documented counts: 369 (Apr 27), 372 (Apr 27), 376 (Apr 28), 696 (May 4 complaint). Data IS growing in Airtable. The dashboard is NOT tracking it. The gap is widening with each passing week. | HIGH |
| F-009 | MEMORY.md Not Updated Since 2026-04-27 | MEMORY.md header says "Last updated: 2026-04-15" and the Last 3 Decisions block shows 2026-04-27 as most recent. The 2026-04-28 audit findings, the 2026-05-01 analytics audit, and any subsequent changes are NOT recorded in MEMORY.md. | MEDIUM |
| F-010 | No Evidence Pipeline is Running | The MetricsRefreshWorker (every 15s live Airtable fetch) is the correct live-data mechanism — but it only runs when `python -m src.siteowlqa.main` is active. There is no evidence in any file read this run that the pipeline is currently running or was running at the time the user observed stale data. | HIGH |

───────────────────────────────────────────────────────────────
                    COMPLIANCE SECTIONS
───────────────────────────────────────────────────────────────

🧠 MEMORY COMPLIANCE:
   - MEMORY.md does NOT contain a literal "data must be live on every page load" 
     directive. What it DOES state (2026-04-27):
       > "Auto-sync: tools/serve_dashboard.py runs git pull on every launch,
       >  ensuring viewers always see admin's latest data."
     And the "Truly Live" architecture (docs/vues_truly_live_architecture.md,
     relayops/state/memory-vues-truly-live.md) specifies:
       - Admin side: MetricsRefreshWorker → Airtable every 15s → output/
       - Viewer side: git pull on launch → latest committed snapshot (~45s lag)
   - The user's expectation ("Airtable live on every page load with no pipeline
     dependency") is STRONGER than what MEMORY.md currently mandates.
   - MEMORY.md is also STALE — last updated 2026-04-27, does not reflect
     findings from 2026-04-28 audit or May 2026 changes.
   - VERDICT: PARTIAL FAIL — MEMORY.md is authoritative but outdated and
     understates the live-data urgency that has been documented in tasks.

📡 LIVE DATA COMPLIANCE:
   - FAIL — Multiple simultaneous violations:
   
   1. ui/*.html files are 7.8MB (baked with embedded static data). Clean 
      templates should be ~17KB. The fix (unbake_html.py) was documented on 
      2026-04-27 but never confirmed applied.
   
   2. ui/team_dashboard_data.json (9.3MB) is a stale git-committed snapshot.
      It has never been proven to match Airtable at time of audit.
   
   3. No runtime fetch() calls were found in the ui/ HTML files (grep confirmed
      zero fetch/loadData/BAKED pattern matches in ui/*.html other than the
      orchestration map). Data is compile-time only.
   
   4. The Truly Live pipeline (4-terminal setup) shows ZERO checkmarks in the
      setup checklist — it has never been confirmed running.
   
   5. Current/live count claims (696 vs 701) are UNVERIFIABLE from this run.
      They must be labeled: "user-reported, possibly stale, not independently 
      verified by this audit."

✅ TRUTHFULNESS COMPLIANCE:
   - PARTIAL:
   - The code in team_dashboard_data.py IS truthful — it correctly fetches
     live records from Airtable via list_dashboard_records(max_records=10000).
     The pipeline design is honest and correct.
   - MetricsRefreshWorker IS truthful — 15s backstop, marks dirty on submission,
     calls refresh_team_dashboard_data() with live Airtable client.
   - run_dashboard_server.py IS truthful — serves output/ with Cache-Control: 
     no-store headers. No stale data from the server layer when pipeline runs.
   - HOWEVER: vues_preview_auto_sync.py is NOT truthful — it checks for 
     hardcoded submission counts (372, 369) that are ~325-327 records behind 
     the actual count. It would NEVER correctly report the current state.
   - HOWEVER: Any documentation claiming "live data" or "auto-syncs every hour" 
     for viewers is not truthful unless the 4-terminal setup is actively running.

🏁 COMPLETION COMPLIANCE:
   - FAIL:
   - RO-003 from 2026-04-28 audit (scout stale data): UNCLOSED, task still in open/
   - RO-004 from 2026-04-28 audit (no fetch() calls): UNCLOSED, task still in open/
   - Truly Live setup checklist: NEVER completed (all 7 items unchecked)
   - No agent has provided evidence that the baked HTML files were ever cleaned
     (unbake_html.py was built and documented but never confirmed applied to ui/)

───────────────────────────────────────────────────────────────
                      REPAIR ORDERS
───────────────────────────────────────────────────────────────

### BLOCKER Priority

[ ] RO-001: UNBAKE ALL ui/*.html FILES IMMEDIATELY
    - Run: python tools/unbake_html.py (already built, never confirmed applied)
    - After: Verify each ui/*.html is ~17KB (not 7.8MB)
    - LIVE_DASHBOARD_GUIDE.md §"The Fix (2026-04-27)" documented this procedure
    - This is the single most impactful fix for the stale-data complaint

[ ] RO-002: CONFIRM WHICH PATH USERS ARE HITTING
    - Verify: Is the dashboard being served from output/ or ui/?
    - If ui/: Switch server path to output/ immediately
    - output/ is served by run_dashboard_server.py with Cache-Control: no-store
    - ui/ is a git-distribution folder — NOT a live-serving path
    - Diagnostic: Check output/dashboard.port — if it exists, a server is running
      on that port serving output/ correctly

[ ] RO-003 (CARRY-FORWARD from 2026-04-28):
    Resolve TASK-20260427-scout-stale-data-blocker — Scout HTML must either:
    (a) Runtime-fetch current submission count from authoritative source, OR
    (b) Be permanently labeled "Last compiled: [timestamp]" with no live implication

[ ] RO-004 (CARRY-FORWARD from 2026-04-28):
    Resolve TASK-20260427-scout-html-live-data — Add fetch() in scout.html
    loadData() with graceful fallback, OR add permanent stale-data banner.

[ ] RO-005: CONFIRM PIPELINE IS RUNNING
    - Open a terminal and run: python -m src.siteowlqa.main
    - Confirm MetricsRefreshWorker thread starts (log: "MetricsRefreshWorker started")
    - Confirm refresh fires: "team_dashboard_data.json updated."
    - Confirm: output/team_dashboard_data.json LastWriteTime is within last 15s

### HIGH Priority

[ ] RO-006: FIX vues_preview_auto_sync.py HARDCODED COUNT CHECKS
    - Lines 57-61: Remove hardcoded checks for 372 and 369
    - Replace with: read actual count from JSON and log it dynamically
    - Current code would never log a correct count at 696+ submissions
    - This tool is supposed to verify live sync — it cannot do so in current state

[ ] RO-007: COMPLETE THE TRULY LIVE SETUP (4-Terminal Architecture)
    - relayops/state/memory-vues-truly-live.md lists all 7 setup checklist items
    - ALL ARE UNCHECKED — this architecture has NEVER been confirmed operational
    - Required terminals: main pipeline, vues_preview_auto_sync.py, 
      auto_commit_push_data.py, browser
    - Required verifications: auto-sync logs show updates, auto-push logs show
      commits, viewer pull test passes
    - Check each item and update the checklist with evidence

[ ] RO-008: VERIFY AIRTABLE RECORD COUNT AUTHORITATIVELY
    - Run: python scripts/verify_scout_count.py (file exists in scripts/)
    - Or: python -c "from src.siteowlqa.airtable_client import ...; ..."
    - Document the authoritative count with timestamp
    - Update ui/team_dashboard_data.json (after pipeline refresh) with fresh data

### MEDIUM Priority

[ ] RO-009: UPDATE MEMORY.md
    - Add session log entry for: 2026-04-28 audit findings (blocker Scout HTML)
    - Add session log entry for: 2026-05-01 analytics audit
    - Add session log entry for: 2026-05-04 stale data BLOCKER complaint
    - Update "Last 3 Decisions" block (currently shows Apr 27 as most recent)
    - Update "Last updated:" header from 2026-04-15

[ ] RO-010: DOCUMENT WHICH COUNT IS AUTHORITATIVE
    - Historical counts: 369 (Apr 27), 372 (Apr 27), 376 (Apr 28), ~696 (May 4)
    - Run authoritative count from Airtable API (RO-008)
    - Record in MEMORY.md under a new "Data Integrity Baseline" section
    - Any future agent claiming a submission count must reference this baseline

───────────────────────────────────────────────────────────────
                   MEMORY UPDATE REQUIREMENTS
───────────────────────────────────────────────────────────────

1. CARRY FORWARD from 2026-04-28 audit:
   - Scout HTML live-data non-compliance (TASK-20260427-scout-html-live-data) 
     remains an ACTIVE BLOCKER. Not resolved as of 2026-05-04.
   - Any agent claiming scout data is "current" or "live" must be flagged BLOCKER.

2. NEW — 2026-05-04:
   - ui/*.html files CONFIRMED still baked (7.8MB each vs expected ~17KB).
     unbake_html.py was built but NEVER confirmed applied to current ui/ files.
   - Truly Live 4-terminal setup: NEVER confirmed operational (all checklist 
     items unchecked as of this audit).
   - vues_preview_auto_sync.py is broken for verification — hardcoded counts 
     are 325+ records behind current Airtable state.

3. MEMORY.md must be updated with the above by the next agent to touch this project.
   Per CLAUDE.md mandate: "Any decision, architectural change, new pattern, or 
   bug root cause → append to MEMORY.md"

───────────────────────────────────────────────────────────────
              ARCHITECTURAL CLARIFICATION FOR MAXIM
───────────────────────────────────────────────────────────────

The VUES codebase has a CORRECT live-data architecture already built.
The problem is it is NOT running / NOT being served from the right path.

Here is the evidence-backed picture:

WHAT IS CORRECT (in code):
✅ team_dashboard_data.py fetches ALL records live from Airtable
   (list_dashboard_records, max_records=10000, no caching)
✅ MetricsRefreshWorker polls every 15 seconds and calls refresh_team_dashboard_data()
✅ run_dashboard_server.py serves output/ with Cache-Control: no-store
✅ The pipeline (python -m src.siteowlqa.main) IS the live-data engine

WHAT IS BROKEN (in deployment):
❌ ui/*.html files are 7.8MB baked snapshots — should be ~17KB clean templates
❌ ui/team_dashboard_data.json is a 9.3MB stale git snapshot
❌ There is no confirmed evidence the pipeline is currently running
❌ The 4-terminal Truly Live setup has never been checked off
❌ Users are likely accessing ui/ files (stale) instead of output/ (live)

THE REQUIRED FIX (in order):
1. Run: python tools/unbake_html.py  (strips baked data from ui/*.html)
2. Run: python -m src.siteowlqa.main  (starts live Airtable pipeline)
3. Access dashboard at: http://localhost:PORT (read from output/dashboard.port)
   NOT from file:// URLs or from ui/ folder directly
4. Optionally run: python tools/vues_preview_auto_sync.py + auto_commit_push_data.py
   for viewer distribution (Truly Live architecture)

THE STALE JSON (ui/team_dashboard_data.json) will only reflect current Airtable
data AFTER the pipeline runs a refresh cycle AND that data is published to ui/ 
via python tools/publish_viewer_data.py.

───────────────────────────────────────────────────────────────
                    FINAL INSTRUCTION
───────────────────────────────────────────────────────────────

TO: Code Puppy / any implementing agent
FROM: Integrity Marshal (integrity-marshal-9e98ec)
RE: VUES Stale Data — Required Actions (2026-05-04)

CONFIRMED BLOCKER. DO NOT claim resolution until:

1. ✅ python tools/unbake_html.py is run AND each ui/*.html is verified ≤ 20KB
2. ✅ python -m src.siteowlqa.main is running AND logs show 
       "team_dashboard_data.json updated." within the last 15 seconds
3. ✅ Dashboard is confirmed accessed via http://localhost:PORT 
       (output/ path), NOT via file:// or ui/ folder
4. ✅ Record count in live dashboard matches Airtable count 
       (run verify_scout_count.py and confirm match)
5. ✅ TASK-20260427-scout-stale-data-blocker and TASK-20260427-scout-html-live-data 
       are closed with evidence, not just moved to done/

UNACCEPTABLE RESPONSES:
- "The architecture supports live data" → not sufficient, DEPLOYMENT must be verified
- "I ran the script" → show log output proving it ran successfully
- "Data is now live" → prove with timestamp + count matching Airtable

This audit is saved at: audits/2026-05-04-vues-stale-data-live-architecture-audit.md

═══════════════════════════════════════════════════════════════
```
