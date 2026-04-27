# SETUP: VUES Truly Live (Option B)

**Goal:** Viewers who clone from git see the exact same data as you, auto-synced through git.

---

## Architecture Overview

```
YOU (Admin)                           VIEWERS (Git Clone)
────────────────────────────────     ────────────────────────────────
SiteOwlQA Admin                       git clone → pull latest
    ↓ (generate data)                     ↓
team_dashboard_data.json              serve_dashboard.py (auto-pull)
    ↓ (30s auto-sync)                    ↓
Auto-rebake HTML                      VUES Preview (browser)
    ↓ (15s auto-push)                    ↓
git commit + push                      Shows same data (LIVE)
    ↓ (viewers auto-pull)
Git Remote (origin/main)
```

---

## Step 1: Verify Git Remote is Configured

```bash
cd C:\VUES
git remote -v
```

Should show:
```
origin  https://... (fetch)
origin  https://... (push)
```

If not configured, ask me to set it up.

---

## Step 2: Rename Shortcuts (Same as Before)

### Shortcut A: SiteOwlQA Launcher → SiteOwlQA Admin
- Right-click → Properties
- Change name to: `SiteOwlQA Admin`
- Optional: Choose green icon (admin)
- Apply → OK

### Shortcut B: VUES Dashboard → VUES Preview
- Right-click → Properties
- Change name to: `VUES Preview`
- Optional: Choose blue icon (preview)
- Apply → OK

---

## Step 3: Start All Four Components (in order)

### **Terminal 1: SiteOwlQA Admin** (Data Generator)

```bash
cd C:\VUES
python -m src.siteowlqa.main
```

Leave running. This generates live scout data.

**You should see:**
```
SiteOwlQA Pipeline Running
Scout submissions: 372
```

---

### **Terminal 2: VUES Preview Auto-Sync** (Rebake Dashboard)

```bash
cd C:\VUES
python tools/vues_preview_auto_sync.py
```

Leave running. Watches data, rebakes every 30s.

**You should see:**
```
VUES Preview Auto-Sync Started
Checking for updates every 30s...
[15:45:30] Scout submissions: 372
```

---

### **Terminal 3: Auto-Push to Git** (Sync with Viewers)

```bash
cd C:\VUES
python tools/auto_commit_push_data.py
```

Leave running. Pushes to git every 15s if data changed.

**You should see:**
```
VUES Auto-Push Started (Truly Live Mode)
Checking for changes every 15s...
[15:45:30] Scout submissions: 372
```

---

### **Terminal 4: VUES Preview Browser**

Click the **VUES Preview** shortcut.

Browser opens → Shows live scout data (372 submissions).

---

## Step 4: Test the Live Sync

### **Test A: Data Changes**

While all 4 terminals running:

1. **In Terminal 1 (SiteOwlQA):** Manually add a test submission (or wait for real one)
2. **In Terminal 2 (Auto-Sync):** Watch for `Scout submissions: 373`
3. **In Terminal 3 (Auto-Push):** Watch for `PUSHED: 373 submissions`
4. **In Browser:** Refresh VUES Preview → should show 373

---

### **Test B: Viewer Experience**

Simulate what viewers see:

```bash
# In a new terminal (Terminal 5)
cd C:\temp
git clone <your-repo-url> vues_viewer_test
cd vues_viewer_test
python tools/serve_dashboard.py
```

Browser opens → Should show 373 (same as your admin panel)

---

## What Each Terminal Logs

### Terminal 1 (Admin)
```
SiteOwlQA Pipeline
Scout submissions: 372
Scout submissions: 373 ← (new submission)
```

### Terminal 2 (Auto-Sync)
```
[15:45:30] Scout submissions: 372
[15:46:00] Checking...
[15:46:15] Scout submissions changed: 372 → 373
[15:46:15] Data updated 15s ago, rebaking...
[15:46:20] Rebake complete
[15:46:20] Scout submissions: 373
```

### Terminal 3 (Auto-Push)
```
[15:45:30] Scout submissions: 372
[15:46:00] Checking...
[15:46:20] Scout submissions changed: 372 → 373
[15:46:20] Data changed, pushing...
[15:46:25] PUSHED: 373 submissions ← SUCCESS
```

### Terminal 4 (Browser)
```
VUES Preview
Scout Program
  Total Submissions: 373
  Completed: 360
  Remaining: 407
```

---

## If Something Goes Wrong

### "Auto-Push says FAILED"

```bash
# Check git status
git status

# If unpushed commits:
git push origin main

# Or manual push:
python tools/push_data_now.py
```

### "Auto-Sync not rebaking"

```bash
# Check if file changed
ls -la output/team_dashboard_data.json
ls -la output/vues_compiled.html

# Manual rebake:
python compile_app.py
```

### "Browser shows old data (372 not 373)"

```bash
# Hard refresh browser
Ctrl + F5 (Windows)
Cmd + Shift + R (Mac)

# Or restart serve_dashboard.py (Terminal 4)
# Click VUES Preview shortcut again
```

---

## Success Criteria

**All 4 should be true:**

✅ Terminal 1: Admin showing submissions (372+)  
✅ Terminal 2: Auto-sync logs showing updates  
✅ Terminal 3: Auto-push logs showing commits  
✅ Terminal 4: Browser showing live data (372+)  

---

## Viewers' Experience (After You Push)

```bash
# Viewers run this (one time)
git clone <your-repo>
cd VUES
python tools/serve_dashboard.py

# Browser opens
# Shows: 373 submissions (same as your admin panel)
# Every time they launch, it auto-pulls latest
```

**They're TRULY LIVE!** 🚀

---

## One More Thing

Every time you push, git history grows. With 4 pushes/min, that's:

- Per day: 5,760 commits
- Per week: 40,320 commits
- Per month: 172,800 commits

Consider:
- Archiving old commits monthly
- Or document: "history will be large"
- Or shallow clone for viewers: `git clone --depth=100`

---

**Ready to start?** Run these 4 terminals and tell me what you see! 🐶
