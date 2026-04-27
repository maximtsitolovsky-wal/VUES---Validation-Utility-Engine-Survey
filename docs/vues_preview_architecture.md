# VUES Preview Architecture

## Overview

**SiteOwlQA Launcher** = Admin Console (Live Data Source)
**VUES Preview** = Live Mirror (Auto-syncs with Admin)

---

## Data Flow

```
SiteOwlQA Launcher (Python Backend)
    ↓ generates
output/team_dashboard_data.json (372 submissions, LIVE)
    ↓ watches
tools/vues_preview_auto_sync.py (checks every 30s)
    ↓ if changed, rebakes
output/vues_compiled.html (372 submissions, FRESH)
    ↓ serves via
serve_dashboard.py (auto-pull from git)
    ↓ browser
VUES Preview (shows 372, LIVE)
```

---

## How It Works

1. **SiteOwlQA Launcher** runs Python pipeline, updates `team_dashboard_data.json`
2. **vues_preview_auto_sync.py** watches data file (30-second intervals)
3. If data changes, auto-runs `compile_app.py` to regenerate HTML with fresh data
4. **VUES Preview** shortcut opens serve_dashboard.py
5. serve_dashboard.py auto-pulls from git (gets latest compiled HTML)
6. Browser shows live data, always in sync with SiteOwlQA Launcher

---

## Verification

Check if auto-sync is working:
```bash
# Terminal 1: Run SiteOwlQA Launcher (admin)
cd C:\VUES
python -m src.siteowlqa.main

# Terminal 2: Run VUES Preview auto-sync
cd C:\VUES
python tools/vues_preview_auto_sync.py

# Terminal 3: Open VUES Dashboard shortcut
# It should show live data, auto-updated
```

---

## Shortcut Configuration

### SiteOwlQA Launcher (Admin)
- Name: `SiteOwlQA Admin`
- Target: `python -m src.siteowlqa.main`
- Working Dir: `C:\VUES`
- Icon: (green, admin theme)

### VUES Dashboard (Preview)
- Name: `VUES Preview`
- Target: `python tools/serve_dashboard.py`
- Working Dir: `C:\VUES`
- Icon: (blue, preview theme)
- Optional: Add `tools/vues_preview_auto_sync.py` as background task

---

## Fallback: Manual Sync

If auto-sync isn't running:
```bash
python compile_app.py && python exact_clone.py
```

This regenerates compiled dashboards with latest data.
