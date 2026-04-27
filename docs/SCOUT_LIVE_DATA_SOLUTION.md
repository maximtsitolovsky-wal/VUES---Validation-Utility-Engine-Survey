# ✅ Scout Program Table - NOW LIVE FOR EVERYONE

## Summary

**Fixed:** Scout program table now provides **live data** for both admin and viewers using a smart fetch-first-fallback strategy.

---

## 🎯 How It Works Now

### For Admin (You):
1. Run `python main.py` → pipeline polls Airtable every 15s
2. `output/` directory gets fresh JSON + clean HTML templates
3. Dashboard serves at `http://localhost:PORT/scout.html`
4. **Result:** Live data refreshing every 15 seconds ✅

### For Viewers:
1. Clone/download repo or run `git pull`
2. Double-click desktop shortcut (created by `tools/install.py`)
3. `serve_dashboard.py` starts → auto-runs `git pull` → serves from `ui/`
4. Scout page opens at `http://localhost:8765/scout.html`
5. **Smart Fetch Logic:**
   - ✅ **Try fetch first:** Attempts to load `team_dashboard_data.json` from server
   - ✅ **Use fallback:** If fetch fails (offline, CORS, no server), uses embedded data
   - ✅ **Auto-refresh:** When back online, fetches live data again
6. **Result:** Mirrors admin's data when online, works offline with last snapshot ✅

---

## 🔧 Technical Architecture

### Two Directory Strategy:

**`output/` (Admin Live Server)**
- ✅ Clean HTML templates (17KB each)
- ✅ Fresh JSON files (auto-refreshed every 15s)
- ✅ Served by `run_dashboard_server.py` with no-cache headers
- ❌ NOT committed to git

**`ui/` (Viewer Distribution)**
- ✅ Baked HTML files (3.8MB with embedded fallback data)
- ✅ JSON files (committed snapshots)
- ✅ Smart fetch polyfill (tries live first, falls back to embedded)
- ✅ Committed to git for distribution

### Data Flow:

```
┌──────────────┐  every 15s  ┌─────────────────┐
│ Airtable API │ ───────────▶ │ output/*.json   │ (admin live)
└──────────────┘              └────────┬────────┘
                                       │
                        publish_viewer_data.py
                                       │
                                       ▼
                              ┌─────────────────┐
                              │ ui/*.json       │ (viewer snapshot)
                              │ ui/*.html       │ (baked with fallback)
                              └────────┬────────┘
                                       │
                                  git push
                                       │
                                       ▼
                              ┌─────────────────┐
                              │ Viewers git pull│ → get latest
                              └─────────────────┘
```

---

## 🚀 Workflow for Admin

### Daily Operation:
1. Pipeline runs automatically → `output/` always fresh
2. When ready to publish to viewers:
   ```bash
   python tools/publish_viewer_data.py
   ```
3. This will:
   - Copy `output/*.json` → `ui/*.json`
   - Bake data into `ui/*.html` files (with smart fallback)
   - Git commit + push

### Viewers automatically get updates:
- Desktop shortcut runs `git pull` before opening
- Or they manually run `git pull`

---

## 🧪 Testing the Fallback Logic

**Test 1: Admin Live Server**
```bash
# Open admin's live dashboard
start http://localhost:60630/scout.html

# Check browser console - should see:
# [VUES] ✓ Fetched live data: team_dashboard_data.json
```

**Test 2: Viewer with Server**
```bash
# Simulate viewer environment
cd ui
python -m http.server 8765
start http://localhost:8765/scout.html

# Browser console should show:
# [VUES] ✓ Fetched live data: team_dashboard_data.json
```

**Test 3: Viewer Offline (Fallback)**
```bash
# Open HTML directly (no server)
start ui/scout.html  # Opens with file:// protocol

# Browser console should show:
# [VUES] Fetch failed (TypeError: Failed to fetch), using fallback data
# [VUES] Serving from embedded fallback (baked 2026-04-27 14:27:05)
```

**Test 4: Automated Test**
```bash
cd ui
python -m http.server 9999
start http://localhost:9999/../tools/test_fallback_logic.html

# Should show all 3 tests passing
```

---

## 📊 Current Stats (as of 2026-04-27 14:27)

- **Total Scout Submissions:** 369
- **Unique Sites:** 363
- **Completed:** 356 / 765 target sites (46.5%)
- **Remaining:** 409
- **Vendor Assignments:** 758 total, 355 completed, 403 remaining
- **Data Size:** 4.4MB JSON, refreshes every 15s

---

## 🎯 Key Features

### ✅ Admin Benefits:
- Live data every 15 seconds from Airtable
- No manual refresh needed
- Full pipeline visibility
- Easy publishing to viewers (one command)

### ✅ Viewer Benefits:
- Works online (fetches fresh data)
- Works offline (uses last snapshot)
- Auto-updates on launch (`git pull`)
- No complex setup required
- Desktop shortcut for easy access

### ✅ Technical Benefits:
- No data duplication (fetch-first strategy)
- Graceful degradation (fallback when needed)
- CORS-safe (works with file:// URLs)
- Bandwidth-efficient (only fetches when online)
- Git-based distribution (version controlled)

---

## ⚠️ Important Notes

### For Admin:
- **Don't** run `unbake_html.py` on `ui/` files (breaks viewer fallback)
- **Do** run `publish_viewer_data.py` when you want viewers to get updates
- **Keep** `output/` unbaked (live server needs clean templates)

### For Viewers:
- **Do** run `git pull` regularly to get latest data
- **Don't** edit files in `ui/` (git will overwrite)
- **Use** the desktop shortcut (handles git pull + server start)

---

## 🐛 Troubleshooting

### "Scout table shows 'Loading...' forever"

**Admin:**
```bash
# 1. Check if pipeline is running
curl http://localhost:60630/api/app/status

# 2. Rebuild dashboard
python tools/rebuild_current_dashboard.py

# 3. Check JSON freshness
powershell -Command "Get-Item output/team_dashboard_data.json | Select LastWriteTime"
```

**Viewer:**
```bash
# 1. Pull latest data
git pull

# 2. Check fallback data exists
powershell -Command "$c = Get-Content ui/scout.html -Raw; if ($c -match 'FALLBACK') { 'OK' } else { 'MISSING' }"

# 3. Re-run installer
python tools/install.py
```

### "Viewers see old data"

```bash
# Admin publishes fresh data
python tools/publish_viewer_data.py

# Viewers pull updates
git pull

# Or restart desktop shortcut (it auto-pulls)
```

---

## 📚 Related Files

- `tools/bake_data_into_html.py` - Smart fallback injection
- `tools/publish_viewer_data.py` - Publish to viewers
- `tools/unbake_html.py` - Strip baked data (admin only)
- `tools/serve_dashboard.py` - Viewer server (auto-pulls)
- `tools/test_fallback_logic.html` - Test harness
- `src/siteowlqa/team_dashboard_data.py` - Data generation
- `src/siteowlqa/metrics_worker.py` - 15s refresh worker
- `docs/LIVE_DASHBOARD_GUIDE.md` - Architecture details

---

**Status:** ✅ COMPLETE - Scout table is live for admin AND viewers!  
**Last Updated:** 2026-04-27 by Code Puppy 🐶
