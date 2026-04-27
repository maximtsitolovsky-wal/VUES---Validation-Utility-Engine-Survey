# Memory: VUES Truly Live Architecture Decision

**Date:** 2026-04-27  
**Decision:** Implement truly live viewer experience with auto-push to git  
**Status:** ACTIVE

---

## Decision

Viewers who clone from git will see **the exact same data as Maxim's admin panel**, auto-synced through git.

**Mechanism:**
1. SiteOwlQA Admin (Maxim) generates live data
2. Auto-sync rebakes dashboards (every 30s)
3. Auto-push commits + pushes to git (every 15s if changed)
4. Viewers clone/pull → see latest data
5. serve_dashboard.py auto-pulls on launch

**Latency:** ~45 seconds from submission to viewer seeing it

---

## Components

| Tool | Interval | Action | Status |
|------|----------|--------|--------|
| tools/vues_preview_auto_sync.py | 30s | Watch data, rebake HTML | ✅ Built |
| tools/auto_commit_push_data.py | 15s | Watch data, commit + push | ✅ Built |
| tools/serve_dashboard.py | On launch | Auto-pull from git | ✅ Existing |

---

## Tradeoffs

**Pro:**
- Viewers always see current data
- Simple architecture (git is source of truth)
- No central server needed

**Con:**
- Git history grows fast (5,760 commits/day)
- Network required for push (VPN dependency)
- Need "don't edit locally" rule for viewers

---

## Gotchas

**Git Conflicts:**
- Viewers who modify local files + git-pull can conflict
- Solution: Tell viewers "read-only clone"

**Network Failures:**
- If VPN down, auto-push queues and retries
- Manual fallback: `python tools/push_data_now.py`

**Large Repo:**
- Consider archiving old commits monthly
- Or implement shallow clones for viewers

---

## Setup Checklist

- [ ] Terminal 1: `python -m src.siteowlqa.main` (SiteOwlQA Admin)
- [ ] Terminal 2: `python tools/vues_preview_auto_sync.py` (auto-rebake)
- [ ] Terminal 3: `python tools/auto_commit_push_data.py` (auto-push)
- [ ] Terminal 4: Click "VUES Preview" shortcut (browser)
- [ ] Verify: Auto-sync logs show submissions updating
- [ ] Verify: Auto-push logs show commits + pushes
- [ ] Test: Viewers clone → pull → see same data

---

## Applies To

- VUES Dashboard (compiled version)
- Scout/Survey/Routing data
- All compiled HTML dashboards (vues_compiled.html, vues_exact_clone.html)

---

## Related Tasks

- TASK-20260427-vues-preview-architecture.md (setup instructions)
- docs/vues_truly_live_architecture.md (detailed documentation)

---

## Success Criteria

When working:
- Maxim adds submission → viewers see it within 45 seconds
- Both UIs show same number
- Git history has new commits every 15s (when data changes)
- Viewers see "auto-pull completed" on VUES Preview launch
