# Repair Order: VUES Dashboard Stale Data

**Severity:** BLOCKER  
**Status:** IN PROGRESS  
**Issued:** 2026-04-27T15:40:00Z

---

## Problem

| System | Shows | Actual | Status |
|--------|-------|--------|--------|
| SiteOwlQA Launcher | 372 subs | 372 subs | LIVE |
| VUES Dashboard | 369 subs | 372 subs | STALE |
| Difference | -3 subs | — | **OUT OF SYNC** |

---

## Root Cause

**VUES Dashboard was compiled/baked BEFORE 3 new submissions were added to SiteOwlQA.**

- Current data (team_dashboard_data.json): 372 scout records
- Compiled scout.html: 369 scout records (old)
- vues_compiled.html: Contains stale data
- vues_exact_clone.html: Contains stale data

---

## Fix Applied

**2026-04-27 15:40:00Z**

1. Ran `compile_app.py` → Regenerated vues_compiled.html with current data (372)
2. Ran `exact_clone.py` → Regenerated vues_exact_clone.html with current data (372)

---

## Verification Required

**User must:**
1. Close VUES Dashboard shortcut (if open)
2. Wait 5 seconds
3. Re-open VUES Dashboard shortcut
4. Navigate to Scout section
5. Verify: Shows 372 submissions (not 369)
6. Report back: "Fixed!" or error/issue

---

## Root Cause Analysis

**Why this happened:**

1. SiteOwlQA Launcher (live Python app) received 3 new submissions
2. SiteOwlQA updated its internal data
3. But VUES Dashboard (compiled HTML) was last baked BEFORE those 3 came in
4. VUES Dashboard still shows old compiled state (369)

**How to prevent:**

- VUES Dashboard should auto-rebake when launched (per MEMORY.md: tools/serve_dashboard.py runs git pull + auto-compile)
- Or scout.html should fetch live data instead of using baked data

---

## Status

Files regenerated. Waiting for user verification.
