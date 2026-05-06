# Task: TASK-20260506-cleanup-deprecate-old-systems

## Metadata
- **Created:** 2026-05-06T11:44:17Z
- **Created-By:** relayops-coordinator-eddf21
- **Priority:** high
- **Status:** in-progress
- **Claimed-By:** code-puppy-565db1
- **Claimed-At:** 2026-05-06T11:44:17Z
- **Last-Updated:** 2026-05-06T11:44:17Z

## Description
Deprecate old systems and clear cache for a clean dashboard. Remove legacy baked HTML files and stale JSON cache to prepare for live-fetch architecture.

## Acceptance Criteria
- [ ] Delete deprecated HTML files from output/
- [ ] Delete deprecated HTML files from ui/
- [ ] Clear stale JSON cache from output/
- [ ] Clear stale JSON cache from ui/
- [ ] Verify protected files remain untouched
- [ ] No errors or broken references after cleanup

## Actions

### 1. Delete Deprecated HTML Files
**Target directories:** `output/` and `ui/`

| File | Reason for Deprecation |
|------|------------------------|
| orchestration_map_deprecated.html | Explicitly marked deprecated |
| vues_compiled.html | Replaced by live-fetch architecture |
| vues_exact_clone.html | Legacy baked approach |
| summary_backup.html | Backup file, no longer needed |
| summary_original.html | Original version, superseded |

### 2. Clear Stale JSON Cache Files
**Target directories:** `output/` and `ui/`

| File | Reason for Clearing |
|------|---------------------|
| realtime_snapshot.json | Stale cache |
| survey_routing_data.json | Stale cache |
| team_dashboard_data.json | Stale cache |
| vues_metrics_current.json | 5 days stale (conflict DATA-STALENESS-20260504-001) |

## 🛡️ PROTECTED FILES - DO NOT TOUCH

| File/Component | Reason Protected |
|----------------|------------------|
| `ui/routing.html` | Awaiting human verification of JS fix (TASK-20260427-routing-zeros) |
| `ui/scout.html` | Live-fetch migration in progress (TASK-20260427-scout-html-live-data) |
| `git_autopush.py` | Recently fixed to prevent ui/ overwrites (commit 73dae97) |
| `loadData()` function | Part of BLOCKER task fix (TASK-20260428-URGENT-viewer-data-integrity) |

## Progress Log
| Timestamp | Agent | Action | Notes |
|-----------|-------|--------|-------|
| 2026-05-06T11:44:17Z | relayops-coordinator-eddf21 | Created | Task created per user request |
| 2026-05-06T11:44:17Z | code-puppy-565db1 | Claimed | Owner assigned, cleanup in progress |

## Blockers
None

## Related Conflicts
- Resolves: DATA-STALENESS-20260504-001 (vues_metrics_current.json staleness)

## Completion Evidence
Pending - will include:
- List of deleted files
- Confirmation protected files untouched
- Post-cleanup directory listing
