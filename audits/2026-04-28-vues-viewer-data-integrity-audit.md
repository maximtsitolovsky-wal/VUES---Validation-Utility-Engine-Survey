# VUES Viewer Data Integrity Audit
- **Audit ID:** integrity-marshal-72bb79-20260428-1136
- **Auditor:** Integrity Marshal (integrity-marshal-72bb79)
- **Audit Time:** 2026-04-28T11:36:02Z
- **Target:** VUES Dashboard — Viewer Data Integrity
- **Scope:** ui/*.html, relayops/tasks/, relayops/state/conflicts.md

---

## VERDICT: PARTIAL
## SEVERITY: BLOCKER

---

## Evidence Gathered This Run

| Source | Verified |
|--------|----------|
| relayops/tasks/claimed/* | ✅ Read |
| relayops/tasks/open/* | ✅ Read |
| relayops/tasks/done/* | ✅ Read |
| relayops/state/conflicts.md | ✅ Read |
| relayops/state/memory-vues-truly-live.md | ✅ Read |
| relayops/state/registry.md | ✅ Read |
| relayops/outbox/human/* | ✅ Read |
| relayops/inbox/agent/* | ✅ Read |
| ui/*.html (VUES_BAKED_VERSION grep) | ✅ Grepped |
| ui/*.html (fallback data grep) | ✅ Grepped |
| docs/VIEWER_SETUP.md | ✅ Read |

---

## FINDINGS TABLE

| # | Category | Finding | Severity |
|---|----------|---------|----------|
| F-001 | Completion Without Evidence | TASK-20260428-URGENT-viewer-data-integrity is in claimed/ with ALL 5 success criteria UNCHECKED — no viewer confirmation received | BLOCKER |
| F-002 | Task Metadata Integrity | TASK-20260427-routing-zeros physically in claimed/ folder but has status: open and owner: unclaimed — inconsistent state | BLOCKER |
| F-003 | Stale Data (Open BLOCKER Task) | TASK-20260427-scout-stale-data-blocker: Scout shows 369 vs actual 372+ submissions. Task OPEN, unresolved | BLOCKER |
| F-004 | No Live Verification | TASK-20260427-scout-html-live-data: Scout HTML has zero runtime fetch() calls. Serves compile-time baked state only. Task OPEN, unresolved | BLOCKER |
| F-005 | Stale Routing Fallback | SURVEY_ROUTING_DATA_FALLBACK baked at 09:21:11 — ~2h 15min before audit. Cannot confirm this matches current authoritative state | HIGH |
| F-006 | False "Live" Claims in Docs | docs/VIEWER_SETUP.md claims "376+ submissions (live data)" and "Data auto-syncs every hour" — neither is verified for viewer machines | HIGH |
| F-007 | Preview Architecture Incomplete | TASK-20260427-vues-preview-architecture in open/ — auto-sync setup checklist mostly unchecked; full pipeline not confirmed operational | HIGH |
| F-008 | Bake Timestamp Anomaly | HTML files show VUES_BAKED_VERSION = '2026-04-28 11:38:09' which is 2 min AFTER audit runtime (11:36:02). Possible clock drift or indicates a very recent bake whose correctness cannot be independently verified | MEDIUM |
| F-009 | Prior Diagnostic: Fetch Routing Returned 3 Sites | Evidence in TASK-20260428-URGENT: "Fetch Routing ✅ PASS - 3 sites" — server-side routing JSON was stale at time of last test. Not re-verified this run | MEDIUM |
| F-010 | Task Marked Done Without Full Evidence | TASK-20260428-viewer-data-loading moved to done/ but all "Open Questions" (specific error, which page, browser console errors) were never answered | MEDIUM |
| F-011 | Auto-Push Root Cause Fixed But Unverified | git_autopush.py fix (commit 73dae97) deployed. Viewer never confirmed successful git pull of this fix (commit 98b2894 also cited) | MEDIUM |
| F-012 | Favicon 404 Persisting | Minor JS console error (favicon.ico 404) reported in two rounds and never resolved | LOW |

---

## COMPLIANCE SECTIONS

### 🧠 MEMORY COMPLIANCE
- **No fake memory claims detected.** Agent operations use relayops task/state files as shared memory — this is a legitimate architecture.
- relayops/state/memory-vues-truly-live.md correctly labeled as an architectural decision record, not a live-state claim.
- ✅ PASS on memory compliance.

### 📡 LIVE DATA COMPLIANCE
- **FAIL — Multiple violations:**
  - Scout HTML pages have NO runtime fetch() calls (F-004). Data is compile-time only. Implicitly presented as current.
  - VIEWER_SETUP.md explicitly claims "live data" and "auto-syncs every hour" (F-006) — unverified for viewer environment.
  - Routing fallback data generated at 09:21, presented as current at 11:36 (F-005). No authoritative check performed during this run.
  - Prior diagnostic confirmed server-side routing JSON had only 3 sites (stale JSON endpoint) — not re-verified.
- ⚠️ All data presented to viewers should be labeled: **"Last compiled: 2026-04-28 09:21 (routing) / 11:38 (HTML bake)"** until live verification is operational.

### ✅ TRUTHFULNESS COMPLIANCE
- **PARTIAL:**
  - HTML fallback data IS present and baked across all pages (✅ confirmed by grep).
  - SURVEY_ROUTING_DATA_FALLBACK shows 774 total_sites — consistent with live JSON (ui/survey_routing_data.json line 4).
  - TEAM_DASHBOARD_DATA_FALLBACK IS present — previous root cause (missing fallback) appears fixed.
  - loadData() stale-data warning banners are in place (analytics.html line 611).
  - BUT: Scout record count discrepancy (369 vs 372 vs 376) across tasks is unresolved — cannot confirm which count is authoritative.
  - BUT: VIEWER_SETUP.md "live data" and "auto-syncs every hour" claims are NOT truthful for the current viewer deployment state.

### 🏁 COMPLETION COMPLIANCE
- **FAIL — Two completion violations:**
  - TASK-20260428-URGENT-viewer-data-integrity: Claimed as fixed (commits 73dae97, 98b2894 cited), but task remains in claimed/ with all 5 success criteria boxes UNCHECKED. No viewer confirmation received. **This is an unsupported completion claim.**
  - TASK-20260428-viewer-data-loading: Moved to done/ but listed "Open Questions" were never answered.
- ✅ PASS: relayops/state/conflicts.md shows both routing conflicts (001, 002) properly resolved with documented evidence and root cause.

---

## REPAIR ORDERS

### Priority: BLOCKER

- [ ] **RO-001:** Obtain explicit viewer confirmation (diagnostic.html results + git log output) before closing TASK-20260428-URGENT-viewer-data-integrity. Do NOT mark done until viewer reports all 5 criteria PASS.
- [ ] **RO-002:** Fix TASK-20260427-routing-zeros metadata — file is in claimed/ but has status: open and owner: unclaimed. Either claim it properly (move to claimed, set owner) or move to open/ to match its metadata.
- [ ] **RO-003:** Resolve TASK-20260427-scout-stale-data-blocker — Scout HTML must either (a) runtime-fetch current submission count from authoritative source or (b) be labeled "Last compiled: [timestamp]" with no live-data implication.
- [ ] **RO-004:** Resolve TASK-20260427-scout-html-live-data — Add fetch() in scout.html loadData() with graceful fallback, or add permanent stale-data banner: "⚠️ Data as of [VUES_BAKED_VERSION]. Not live-updating."

### Priority: HIGH

- [ ] **RO-005:** Correct VIEWER_SETUP.md — Remove "live data" claim from "376+ submissions (live data)" line. Replace with: "376+ submissions (as of last bake)". Remove or qualify "Data auto-syncs every hour" — this is architecture intent, not a guaranteed viewer behavior.
- [ ] **RO-006:** Complete TASK-20260427-vues-preview-architecture — Run and verify all 4 terminals in the "truly live" setup. Check each item on the setup checklist and document results. If not operational, notify viewers that data currency is limited to git pull cadence.

### Priority: MEDIUM

- [ ] **RO-007:** Clarify bake timestamp anomaly — VUES_BAKED_VERSION '2026-04-28 11:38:09' is 2 minutes after audit time 11:36:02. Document whether this is expected (bake ran just before audit) or a clock drift issue. If clock drift, normalize timestamps.
- [ ] **RO-008:** Re-verify server-side routing JSON freshness — Prior diagnostic showed fetch returning only 3 sites. Confirm ui/survey_routing_data.json (537KB, 774 sites per line 4) is being served correctly and matches the authoritative source.
- [ ] **RO-009:** Answer TASK-20260428-viewer-data-loading open questions and add evidence section before treating this as fully done.
- [ ] **RO-010:** Establish a definitive scout submission count — tasks reference 369, 372, and 376 at different points. Document which is current and authoritative, and verify HTML fallback matches.

### Priority: LOW

- [ ] **RO-011:** Fix favicon.ico 404 — Add missing favicon to ui/assets/ and reference it in all HTML files. Eliminates persistent console noise obscuring real errors.

---

## MEMORY UPDATE REQUIREMENTS

1. **DO NOT mark viewer integrity as resolved** until RO-001 is complete with viewer-side confirmation.
2. **Scout HTML live-data non-compliance** (TASK-20260427-scout-html-live-data) remains an ACTIVE BLOCKER per prior Integrity Marshal notice. Any agent claiming scout data is "current" or "live" must be flagged.
3. **git_autopush.py fix** (commit 73dae97) is unverified on viewer side — do not assume viewers have this fix until git pull is confirmed.
4. **Routing data freshness** — baked fallback is from 09:21 this morning. This must be re-evaluated after the next admin data generation cycle.

---

## WHAT IS WORKING (Evidence-Backed)

| Item | Evidence |
|------|----------|
| TEAM_DASHBOARD_DATA_FALLBACK present in all HTML | Confirmed by grep across analytics, diagnostic, howitworks, index, scout, survey, summary, routing |
| SURVEY_ROUTING_DATA_FALLBACK present with 774 sites | Confirmed by grep across all UI pages |
| Stale-data warning banner in loadData() | analytics.html line 611 confirmed |
| Bulletproof loadData() with visible error handling | analytics.html lines 599-635 confirmed |
| Fetch polyfill + file:// protocol detection | analytics.html lines 176-245 confirmed |
| Both routing conflicts RESOLVED with root cause | relayops/state/conflicts.md confirms JS syntax fix |
| diagnostic.html exists for viewer troubleshooting | File present, bake version set |

---

## FINAL INSTRUCTION

**To Operators / human:maxim:**

The VUES viewer data pipeline has been significantly hardened (baked fallbacks present, stale warnings added, git_autopush bug fixed), but the system **cannot be declared viewer-ready** until:

1. A viewer sends back diagnostic.html results confirming all PASS — this step is MISSING and BLOCKING.
2. Scout HTML live-data claim is resolved (open BLOCKER task for 1+ day).
3. VIEWER_SETUP.md is corrected to remove unsupported "live data" and "auto-syncs every hour" claims.

**Current safe statement for viewers:**
> "VUES Dashboard shows data as of the last bake (2026-04-28 ~09:21 for routing, ~11:38 for HTML). Data is not live-updating. Run `git pull` + restart dashboard to receive the latest baked snapshot."

**Do NOT communicate "live data" to viewers until the truly-live architecture (RO-006) is confirmed fully operational.**
