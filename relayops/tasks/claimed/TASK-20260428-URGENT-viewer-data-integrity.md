# Task

## Metadata

- id: TASK-20260428-URGENT-viewer-data-integrity
- title: BLOCKER - Viewer dashboard shows empty data, cross-functional sharing broken
- created_by: human:maxim
- owner: agent:code-puppy-4192f5
- status: claimed
- priority: urgent
- created_at: 2026-04-28T10:45:00Z
- updated_at: 2026-04-28T10:50:00Z
- expires_at: 2026-04-28T12:00:00Z

## Objective

Fix viewer data loading so cross-functional teams can access shared VUES dashboard data.

## Severity

**BLOCKER** - Data sharing integrity is compromised. Viewers cannot see any data.

## Current Evidence

### Diagnostic Results from Viewer Machine (10:35 AM)
| Test | Result | Implication |
|------|--------|-------------|
| Fallback Data Variable | ❌ FAIL - undefined | HTML not baked on viewer |
| Baked Version | ❌ FAIL - not set | HTML not baked on viewer |
| Fetch JSON | ✅ PASS - 376 records | Server works, JSON exists |
| Fetch Routing | ✅ PASS - 3 sites | Data is STALE (should be 700+) |

### Root Cause Hypothesis
1. Viewer's local files are STALE - git pull not working or not run
2. Auto-pull in serve_dashboard.py is silently failing
3. Viewer may have network/auth issues with git

## Integrity Marshal Violations

Per Integrity Marshal rules:
- **Live Data Claim Without Verification**: Dashboard implicitly claims "current" data but serves stale/empty
- **Stale Memory Reuse**: Viewer using old cached HTML without fresh baked data
- **Completion Without Evidence**: Previous "fix" commits didn't verify viewer-side functionality

## Required Fix

### Immediate Actions (Agent) — COMPLETED
1. ✅ Verified baked data is in git remote
2. ✅ Created bulletproof loadData() with visible error handling
3. ✅ loadData() tries fetch first, shows warning if using fallback
4. ✅ Added visible error banners and stale data warnings
5. ✅ Pushed fixes (commit `98b2894`)
6. ⏳ Awaiting viewer verification

### Viewer Actions Required
1. Run `git pull` and report output
2. Run diagnostic.html and report results
3. Check browser console for JS errors

## Success Criteria

- [ ] Viewer sees actual data (376+ scout records)
- [ ] Diagnostic shows all PASS
- [ ] No "Loading..." forever
- [ ] Data freshness is visible to user

## Constraints

- Cannot access viewer machine directly
- Must work without manual intervention after git pull
- Must degrade gracefully if git pull fails
