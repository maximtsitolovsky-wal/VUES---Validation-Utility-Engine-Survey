# BLOCKER: Scout HTML Showing Stale Data

**Severity:** BLOCKER  
**Status:** Integrity Marshal Alert  
**Reported:** 2026-04-27T15:35:00Z

---

## Evidence

| Observation | Value | Source |
|-------------|-------|--------|
| Scout.html displays | 369 submissions | User visual inspection |
| Actual current | 372 submissions | User verification |
| Discrepancy | -3 submissions | Clear data mismatch |
| Freshness | STALE | Data is outdated |

---

## Compliance Violation

**Scout HTML claims to show current/live data but displays stale values.**

Per Integrity Marshal mandate:
> "Any agent making current, live, latest, real-time claims must prove the data was checked during the current run against an authoritative source."

**Scout.html fails this requirement:**
- ❌ No live verification during page load
- ❌ Displays stale data (369 vs actual 372)
- ❌ No freshness timestamp shown
- ❌ No "Last Known" label

---

## Required Action

1. **Identify** where 369 comes from (baked data? outdated JSON endpoint?)
2. **Connect** scout.html to live/current data source
3. **Add timestamp** showing when data was last verified
4. **Add label** if not live-updating: "Last compiled: [timestamp]"
5. **Test** that scout.html shows 372+ (or current number)
6. **Verify** that 3 new submissions are visible

---

## Interim Status

Scout.html is **BLOCKED from production use** until live data verification is implemented.

Task created: `TASK-20260427-scout-html-live-data.md`  
Escalation: Integrity Marshal notification sent
