# Task

## Metadata

- id: TASK-20260428-viewer-data-loading
- title: Viewer version not loading data
- created_by: human:maxim
- owner: agent:code-puppy-4192f5
- status: claimed
- priority: high
- created_at: 2026-04-28T10:05:00Z
- updated_at: 2026-04-28T10:05:00Z
- expires_at: none

## Objective

Fix data loading issue in the viewer version of VUES dashboard.

## Context

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
