# VUES Truly Live Architecture

## Overview

**For Maxim (Admin):**
- SiteOwlQA Admin runs live pipeline
- VUES Preview auto-syncs (updates every 30s)
- Auto-push syncs to git (pushes every 15s if changed)

**For Viewers (Git Clone):**
- `git clone` → get latest pushed data
- `serve_dashboard.py` → auto-pulls fresh commits
- Browser shows → same as Maxim (truly live mirror)

---

## Data Flow

```
SiteOwlQA Admin (Maxim's control panel)
    ↓ new submission
output/team_dashboard_data.json (372 → 373)
    ↓ (30s auto-sync detects change)
tools/vues_preview_auto_sync.py
    ↓ rebakes
output/vues_compiled.html (373)
    ↓ (15s auto-push detects change)
tools/auto_commit_push_data.py
    ↓ commits + pushes
Git Remote (origin/main)
    ↓ (viewers auto-pull on launch)
Viewer's machine (git clone)
    ↓
serve_dashboard.py (auto-pull runs)
    ↓
Browser (viewer sees 373, SAME as Maxim)
```

---

## Components

### 1. VUES Preview Auto-Sync (30s intervals)
**File:** `tools/vues_preview_auto_sync.py`

Watches: `output/team_dashboard_data.json`
- If changed: runs `compile_app.py`
- Result: `vues_compiled.html` always current

**Status:** ✅ Built, runs locally

### 2. Auto-Push to Git (15s intervals)
**File:** `tools/auto_commit_push_data.py`

Watches: `output/team_dashboard_data.json`, `output/vues_compiled.html`
- If changed: commits + pushes to origin/main
- Result: Viewers can pull fresh data

**Status:** ✅ Built, needs to run

### 3. Serve Dashboard (on launch)
**File:** `tools/serve_dashboard.py` (existing)

On launch: Runs `git pull --ff-only`
- Result: Viewers always see latest pushed data

**Status:** ✅ Already built

---

## Setup for Maxim

### Terminal 1: SiteOwlQA Admin (Pipeline)
```bash
cd C:\VUES
python -m src.siteowlqa.main
```

Generates live data.

### Terminal 2: VUES Preview Auto-Sync
```bash
cd C:\VUES
python tools/vues_preview_auto_sync.py
```

Watches data, rebakes every 30s.

### Terminal 3: Auto-Push to Git
```bash
cd C:\VUES
python tools/auto_commit_push_data.py
```

Watches data, pushes every 15s if changed.

### Terminal 4: VUES Preview (Browser)
```
Click "VUES Preview" shortcut
```

Shows live data, auto-pulled from git.

---

## What Viewers See

After cloning:
```bash
git clone <repo>
cd VUES
python tools/serve_dashboard.py
```

Browser opens → VUES Preview → **shows latest from git**

When Maxim adds submission:
1. SiteOwlQA Admin: +1 submission (373)
2. Auto-sync (30s): Rebakes
3. Auto-push (15s): Commits + pushes
4. Viewer: Clicks VUES Preview → auto-pulls → sees 373

**Latency: ~45s from submission to viewer seeing it**

---

## Fallback (If Auto-Push Fails)

Manual push:
```bash
python tools/push_data_now.py
```

---

## Gotchas

**Git Conflicts:**
- If viewer modified local files and does `git pull`, they might get conflicts
- Solution: Tell viewers "don't edit files locally" or use separate branches

**Network/VPN:**
- Git push requires network access
- If VPN disconnects, auto-push will backoff and retry

**Large Git History:**
- Pushing every 15s = ~4 commits/min = 5,760 commits/day
- Git history will grow fast
- Solution: Archive old commits monthly or use shallow clones

---

## Verification

**Maxim's side:**
```
Terminal 2 (auto-sync):
[15:45:30] Scout submissions: 372
[15:46:00] Scout submissions: 373

Terminal 3 (auto-push):
[15:46:00] Scout submissions changed: 372 → 373
[15:46:02] Data changed, pushing...
[15:46:05] PUSHED: 373 submissions
```

**Viewer's side:**
```
Open VUES Preview → auto-pulls from git → sees 373 (matches Maxim)
```

---

## Success Criteria

✅ Admin adds submission  
✅ Auto-sync rebakes (30s)  
✅ Auto-push commits (15s)  
✅ Viewer sees same number (pulls on next launch)  

**Truly live mode = ACTIVE** 🚀
