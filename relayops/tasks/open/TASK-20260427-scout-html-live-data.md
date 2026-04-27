# Integrity Marshal Notice: Scout HTML Non-Compliance

**Filed:** 2026-04-27T15:31:00Z  
**Agent:** code-puppy-473c30  
**Severity:** BLOCKER  
**Status:** Documented for remediation

---

## Issue

Scout HTML components (`ui/scout.html`, `output/scout.html`, and compiled dashboards) are displaying survey data WITHOUT verifying against live/authoritative sources during page load.

**Violation Type:** Live Data Claim Without Verification

**Integrity Marshal Rule Triggered:**
> "Any agent making current, live, latest, real-time, deployed, available, working, passing, synced, fresh, or production-state claims must prove the data was checked during the current run against an authoritative source."

---

## Current State

| Aspect | Status |
|--------|--------|
| Data Source | Baked into HTML at compile time |
| Live Verification | None (no runtime fetch() calls) |
| Freshness Check | Not performed |
| Authoritative Check | Not performed |
| What Page Shows | Last-compiled state |
| What Page Claims (implicitly) | Current state |

---

## Required Fix

Scout HTML must be refactored to:

1. **At page load:** Fetch current survey data from live source
2. **On init:** `loadData()` must hit authoritative API/JSON endpoint
3. **Display freshness:** Show timestamp of when data was verified
4. **Relabel data:** Mark as "Last Known" + timestamp if live verification unavailable

---

## Interim Requirement

Scout HTML must display:
```html
⚠️ Data compiled: [timestamp]
Not live-updating. Refresh page for current data.
```

---

## Documented In

- File: `C:\Users\vn59j7j\Documents\BaselinePrinter\SVG_IN\integrity_marshal.md`
- Section: "Known Non-Compliant Components"
- Status: BLOCKER, awaiting remediation

---

## Memory Update

This issue is now tracked in Integrity Marshal as a known non-compliance.

**Any future claims that scout data is "current" or "live" will be flagged as BLOCKER unless runtime fetch verification is added.**
