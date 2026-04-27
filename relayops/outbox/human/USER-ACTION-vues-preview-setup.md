# User Action: Rename Shortcuts + Verify Live Sync

---

## Step 1: Rename Shortcuts

### Shortcut A: SiteOwlQA Launcher → SiteOwlQA Admin

1. Right-click: `C:\Users\vn59j7j\OneDrive - Walmart Inc\Desktop\SiteOwlQA Launcher.lnk`
2. Select **Properties**
3. Click **Change Icon** button (if available)
   - Look for a **green** admin-style icon
   - Or leave default
4. Click in the Name field, change to: `SiteOwlQA Admin`
5. **Apply** → **OK**

### Shortcut B: VUES Dashboard → VUES Preview

1. Right-click: `C:\Users\vn59j7j\OneDrive - Walmart Inc\Desktop\VUES Dashboard.lnk`
2. Select **Properties**
3. Click **Change Icon** button (if available)
   - Look for a **blue** preview-style icon
   - Or leave default
4. Click in the Name field, change to: `VUES Preview`
5. **Apply** → **OK**

---

## Step 2: Start Auto-Sync (Terminal 1)

```bash
cd C:\VUES
python tools/vues_preview_auto_sync.py
```

You should see:
```
VUES Preview Auto-Sync Started
Checking for updates every 30s...
Repo: C:\VUES
Data: C:\VUES\output\team_dashboard_data.json
[15:45:30] Scout submissions: 372
```

**Leave this running.**

---

## Step 3: Run SiteOwlQA Admin (Terminal 2)

```bash
cd C:\VUES
python -m src.siteowlqa.main
```

This is the live data source. Let it run.

---

## Step 4: Open VUES Preview (Terminal 3 or New Window)

Click the **VUES Preview** shortcut.

Browser should open and show:
- Scout section: **372 submissions** (matches Admin)
- All data live-synced

---

## Step 5: Test Sync

1. **Admin (SiteOwlQA):** Add a new submission (manually or via test)
2. **Auto-Sync (Terminal 1):** Will log `Scout submissions: 373` within 30s
3. **Preview (Browser):** Will refresh and show 373

---

## What You Should See

**Terminal 1 (Auto-Sync):**
```
[15:45:30] Scout submissions: 372
[15:46:00] Checking...
[15:46:30] Data updated 5s ago, rebaking...
[15:46:35] Rebake complete
[15:46:35] Scout submissions: 373
```

**Browser (VUES Preview):**
```
Scout Program
- Total Submissions: 373 ← (was 372, now LIVE)
- Completed: 360
- Remaining: 407
```

---

## Success Criteria

✅ Auto-Sync running (shows "Scout submissions: 372+")  
✅ SiteOwlQA Admin running (live pipeline)  
✅ VUES Preview open (shows 372, matches Admin)  
✅ Both shortcuts renamed  

**If all 3 are YES: Architecture is LIVE!**

---

## If It Doesn't Work

1. **Preview shows 369 (old number):** 
   - Auto-sync not running. Check Terminal 1.
   - Or manually: `python compile_app.py`

2. **Terminal 1 shows errors:**
   - Post the error message here

3. **Auto-sync stuck:**
   - Press Ctrl+C to stop
   - Run: `python compile_app.py` manually
   - Restart auto-sync

---

**Ready to set it up?** 🐶
