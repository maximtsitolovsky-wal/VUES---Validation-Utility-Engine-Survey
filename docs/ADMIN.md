# 🔧 VUES Admin Guide

> **You are the Admin.** This machine runs the pipeline and publishes data to viewers.

---

## Your Commands

### Start the Pipeline
```powershell
python -m src.siteowlqa.main
```
Polls Airtable every 60 seconds, grades submissions, updates dashboards.

### Publish Data to Viewers
```powershell
python tools/publish_viewer_data.py
```
Copies latest JSON data to `ui/`, commits, and pushes to GitHub.
Viewers will see your updates when they `git pull` or re-download.

### Open Dashboard (Local)
Double-click **VUES Dashboard** on your desktop, or:
```powershell
python tools/serve_dashboard.py
```

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  YOUR MACHINE (Admin)                                       │
│                                                             │
│  python -m src.siteowlqa.main                               │
│       ↓                                                     │
│  Polls Airtable → Grades → Generates output/                │
│       ↓                                                     │
│  python tools/publish_viewer_data.py                        │
│       ↓                                                     │
│  Copies to ui/ → git commit → git push                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
                     GitHub Repo
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  VIEWER MACHINES                                            │
│                                                             │
│  git pull (or re-download ZIP)                              │
│       ↓                                                     │
│  python tools/install.py                                    │
│       ↓                                                     │
│  Desktop shortcut → Dashboard with YOUR data                │
└─────────────────────────────────────────────────────────────┘
```

---

## File Locations

| What | Where |
|------|-------|
| Pipeline output (your live data) | `output/` |
| Viewer data (committed to git) | `ui/*.json` |
| Publish script | `tools/publish_viewer_data.py` |
| Dashboard server | `tools/serve_dashboard.py` |
| This guide | `docs/ADMIN.md` |

---

## Quick Checklist

- [ ] Pipeline running? `python -m src.siteowlqa.main`
- [ ] Data published? `python tools/publish_viewer_data.py`
- [ ] GitHub up to date? `git status` should show "nothing to commit"

---

*You're the boss. Viewers just see what you publish.* 🐕
