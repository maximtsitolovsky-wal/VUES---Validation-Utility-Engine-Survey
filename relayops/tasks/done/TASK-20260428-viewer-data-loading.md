# Task

## Metadata

- id: TASK-20260428-viewer-data-loading
- title: Viewer version not loading data
- created_by: human:maxim
- owner: agent:code-puppy-4192f5
- status: done
- priority: high
- created_at: 2026-04-28T10:05:00Z
- updated_at: 2026-04-28T10:20:00Z
- expires_at: none

## Objective

Fix data loading issue in the viewer version of VUES dashboard.

## Resolution (2026-04-28)

**Root Cause:** Viewer's HTML files didn't have baked fallback data. Their `git pull` was silently failing.

**Evidence from diagnostic:**
- ❌ `window.TEAM_DASHBOARD_DATA_FALLBACK` = undefined
- ❌ `VUES_BAKED_VERSION` = not set  
- ✅ Fetch worked but returned stale data (only 3 sites instead of 700+)

**Fixes Applied:**
1. Re-baked all HTML files with latest data (4.4MB each)
2. Pushed baked HTML to git (`b1da203`)
3. Updated `serve_dashboard.py` to show warning popup when git pull fails
4. Added `diagnostic.html` page for future troubleshooting

**Viewer Action Required:**
```bash
cd VUES---Validation-Utility-Engine-Survey
git pull
```
Then restart the dashboard.

---

## Original Context

User reports "not having data loaded into the viewer version". Need to diagnose:
1. What exactly is broken (which data, which page, what error)
2. Is data baked into HTML files?
3. Is data pushed to git remote?
4. Can viewers fetch data successfully?

## Current State (Verified 2026-04-28 10:03)

| Check | Result |
|-------|--------|
| JSON files exist in ui/ | ✅ team_dashboard_data.json (5.3MB), survey_routing_data.json (500KB) |
| Baked version timestamp | ✅ 2026-04-28 10:17:24 |
| Git status | ✅ Clean, up to date with origin/main |
| FALLBACK data in HTML | ✅ Present (5 references found) |

## Open Questions

1. **What specific error is the viewer seeing?**
2. **Which page/section shows no data?**
3. **Is this a fresh clone or existing install?**
4. **Browser console errors?**

## Inputs

- User report of issue
- ui/*.html files
- ui/*.json files
- tools/bake_data_into_html.py
- tools/serve_dashboard.py

## Output

Working viewer version with data loading correctly.

## Steps

1. Get specific failure details from user
2. Run Integrity Marshal audit on data pipeline
3. Identify root cause
4. Implement fix
5. Verify with user

## Constraints

- Must work for git clone AND local file opening
- Data must be baked as fallback
- Live fetch should work when server is running
