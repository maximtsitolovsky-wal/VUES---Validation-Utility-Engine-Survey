# VUES Follow-the-Leader Architecture

## Status: VERIFIED WORKING ✅

**Date:** 2026-04-27  
**Scout Submissions:** 375 (both Leader and Follower in sync)

---

## Shortcut Configuration

### VUES Admin (LEADER)

| Property | Value |
|----------|-------|
| **File** | `VUES Admin.lnk` |
| **Target** | `powershell.exe` |
| **Script** | `ops\windows\launch_vues_dashboard.ps1` |
| **Mode** | Admin (pipeline + autopush) |
| **Icon** | Gear (shell32.dll,144) |
| **Description** | VUES Admin - Live Pipeline Control (Leader) |

**What it does:**
1. Validates dependencies
2. Starts pipeline (live data generation)
3. Starts git autopush (auto-commits changes)
4. Rebuilds dashboard
5. Opens browser with live data

### VUES Preview (FOLLOWER)

| Property | Value |
|----------|-------|
| **File** | `VUES Preview.lnk` |
| **Target** | `.venv\Scripts\pythonw.exe` |
| **Script** | `tools\serve_dashboard.py` |
| **Mode** | Viewer (read-only) |
| **Icon** | VUES icon (assets\vues_icon.ico) |
| **Description** | VUES Preview - Live Dashboard (Follower/Viewer) |

**What it does:**
1. Auto-pulls from git (gets latest data)
2. Serves dashboard files
3. Opens browser with synced data

---

## Data Flow

```
VUES Admin (Leader)
    ↓ generates
output/team_dashboard_data.json (375 submissions)
    ↓ git autopush (every 15s)
Git Remote (origin/main)
    ↓ git pull (on launch)
VUES Preview (Follower)
    ↓ serves
Browser (375 submissions - SYNCED)
```

---

## Verification

**Test performed:** 2026-04-27

| Component | Scout Submissions | Status |
|-----------|------------------|--------|
| LEADER (team_dashboard_data.json) | 375 | ✅ |
| FOLLOWER (port 51760) | 375 | ✅ |
| FOLLOWER (port 8765) | 375 | ✅ |

**Result:** PERFECT SYNC

---

## For Viewers

When viewers clone the repo:

```bash
git clone <repo-url>
cd VUES

# Option A: Use the shortcut (if installed)
# Click "VUES Preview" shortcut

# Option B: Run directly
python tools/serve_dashboard.py
```

**They will see:**
- Same data as VUES Admin (375 submissions)
- Auto-pulled fresh on every launch
- No stale data issues

---

## Architecture Benefits

1. **Single source of truth:** VUES Admin generates all live data
2. **Automatic sync:** Git autopush + auto-pull keeps everything fresh
3. **Clear roles:** Admin = control, Preview = view
4. **Viewer-friendly:** No pipeline needed, just serve files
5. **Truly live:** ~45 second latency from Admin to Viewer

---

## Files Changed

- `SiteOwlQA Launcher.lnk` → `VUES Admin.lnk` (renamed + icon updated)
- `VUES Dashboard.lnk` → `VUES Preview.lnk` (renamed)
- `tools/auto_commit_push_data.py` (auto git sync)
- `tools/vues_preview_auto_sync.py` (auto rebake)
- `docs/vues_truly_live_architecture.md` (documentation)
