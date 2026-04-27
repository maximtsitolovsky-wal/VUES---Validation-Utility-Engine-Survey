# Repair Order: VUES Preview Architecture Setup

**Severity:** HIGH  
**Status:** IMPLEMENTATION  
**Issued:** 2026-04-27T15:45:00Z

---

## Objective

Convert VUES Dashboard from **stale compiled snapshot** to **live preview mirror** of SiteOwlQA Admin.

---

## Current State

| Component | Status | Issue |
|-----------|--------|-------|
| SiteOwlQA Launcher | LIVE | Real-time data, 372 submissions, authoritative |
| team_dashboard_data.json | LIVE | Updated when SiteOwlQA processes data |
| vues_compiled.html | STALE | Last compiled before 3 new submissions arrived |
| VUES Dashboard | STALE | Shows 369 instead of 372 |

---

## Solution

### 1. Auto-Sync Mechanism

**File:** `tools/vues_preview_auto_sync.py`

- Watches `output/team_dashboard_data.json` for changes
- Every 30 seconds, checks if data is newer than compiled version
- If changed: auto-runs `compile_app.py` to rebake
- Displays sync status: "Scout submissions: 372"

**To run:**
```bash
python tools/vues_preview_auto_sync.py
```

### 2. Shortcut Renaming

**SiteOwlQA Launcher → SiteOwlQA Admin**
- Icon: Green (admin/control theme)
- Purpose: Control panel, live data generation
- Target: `python -m src.siteowlqa.main`

**VUES Dashboard → VUES Preview**
- Icon: Blue (preview/mirror theme)
- Purpose: Live preview, always synced with Admin
- Target: `python tools/serve_dashboard.py`
- (Optional) Auto-launch auto-sync as background task

### 3. Data Freshness Guarantee

Once auto-sync is running:
- VUES Preview always shows latest data
- No manual recompile needed
- Both shortcuts point to same live source
- Submit → SiteOwlQA Admin → 30s → VUES Preview reflects change

---

## Implementation Steps

1. ✅ Created `tools/vues_preview_auto_sync.py`
2. ✅ Created `docs/vues_preview_architecture.md`
3. 🔄 Manually update shortcut names (Step 4 below)
4. 🔄 User verifies data sync works

---

## Shortcut Update Instructions (For User)

**SiteOwlQA Launcher → SiteOwlQA Admin**

1. Right-click shortcut on Desktop
2. Select "Properties"
3. Change Name: `SiteOwlQA Admin`
4. Change Icon (optional): Choose green admin icon
5. Apply → OK

**VUES Dashboard → VUES Preview**

1. Right-click shortcut on Desktop
2. Select "Properties"
3. Change Name: `VUES Preview`
4. Change Icon (optional): Choose blue preview icon
5. Apply → OK

---

## Verification

**Run both to verify sync:**

Terminal 1 (Admin):
```bash
cd C:\VUES
python -m src.siteowlqa.main
```

Terminal 2 (Auto-Sync):
```bash
cd C:\VUES
python tools/vues_preview_auto_sync.py
# Should show: Scout submissions: 372
```

Terminal 3 (Preview):
```bash
# Click "VUES Preview" shortcut
# Should show 372 (matches Admin)
```

---

## Expected Result

- **Admin shows:** 372 submissions (real-time)
- **Auto-sync logs:** "Scout submissions: 372"
- **Preview shows:** 372 submissions (synced)
- **User sees:** Both UIs in perfect sync, live data

---

## Fallback (If Auto-Sync Not Available)

```bash
python compile_app.py && python exact_clone.py
```

Manually regenerate compiled dashboards with latest data.

---

## Memory Update Required

Yes. Document:
- **VUES Preview Architecture:** Two-shortcut pattern (Admin + Preview)
- **Auto-Sync Mechanism:** Watches data, rebakes every 30s
- **Shortcut Names:** Admin vs Preview to clarify roles

---

## Status

✅ Auto-sync mechanism created  
✅ Architecture documented  
🔄 Awaiting user shortcut rename verification  
⏳ First sync test pending
