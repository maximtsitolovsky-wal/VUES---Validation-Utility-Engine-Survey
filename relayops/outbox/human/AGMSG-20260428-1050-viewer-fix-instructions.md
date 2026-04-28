# Agent Message

- id: AGMSG-20260428-1050-viewer-fix-instructions
- from_agent: code-puppy-4192f5
- to_agent: human:viewer
- intent: request
- related_task: TASK-20260428-URGENT-viewer-data-integrity
- state_dependency: none
- action_required: yes

## Summary

URGENT fix deployed - viewer must run these exact steps to get working dashboard.

## Details

We identified and fixed the root cause:
1. Viewer's HTML files were missing baked fallback data
2. loadData() function had no visible error handling - failures were silent
3. No indication to user when data was stale

**Fixes deployed (commit `98b2894`):**
- All HTML files now have bulletproof loadData() with visible error banners
- Stale data warning shows when using fallback
- Error messages visible if rendering fails
- Fresh data baked into HTML (376 scout records, 700+ routing sites)

## Required Viewer Actions

**Step 1: Pull the fixes**
```powershell
cd VUES---Validation-Utility-Engine-Survey
git pull
```
Expected output: `7 files changed` or similar (NOT "Already up to date")

**Step 2: Verify the pull worked**
```powershell
git log --oneline -1
```
Expected: Shows `98b2894 fix(URGENT): bulletproof loadData...`

**Step 3: Restart dashboard**
1. Close any browser tabs with VUES
2. Close any terminal windows running the server
3. Double-click the VUES Dashboard shortcut

**Step 4: Check the diagnostic**
Go to: http://localhost:8765/diagnostic.html

**Report back:**
- Screenshot of diagnostic page results
- Any error banners shown on the dashboard
- The git log output from Step 2

## Verification Criteria

Dashboard is working when:
- [ ] Diagnostic shows all PASS (no red boxes)
- [ ] Scout page shows 376+ records
- [ ] Routing page shows 700+ sites
- [ ] No "Loading..." stuck states
- [ ] No error banners (or only yellow "stale data" warning)

## If Still Failing

1. Check browser console (F12 → Console tab) for red errors
2. Copy error text and report back
3. Try: `git reset --hard origin/main && git pull`
