# VUES Routing Data Integrity Audit
**Date:** 2026-05-04  
**Time:** 12:15 PM  
**Status:** 🚨 CRITICAL DATA MISMATCH DETECTED

---

## Executive Summary

**FINDING:** The dashboard is displaying STALE data from an outdated file. The fresh routing data exists in `output/` but was NOT synced to `ui/` where the dashboard reads from.

**IMPACT:** Dashboard viewers are seeing incorrect routing status for 768 sites:
- ❌ Shows 215 sites requiring REVIEW (should be 0)
- ❌ Shows 553 sites ready to assign (should be 661)
- ❌ Missing 107 sites pending scout submission
- ❌ ALL sites incorrectly marked as scout_submitted: False

**ROOT CAUSE:** The `ui/survey_routing_data.json` file is 2 minutes older than `output/survey_routing_data.json` and was not synced by `bake_data_into_html.py`.

---

## Detailed Comparison

### File Metadata

| File | Timestamp | Size | Status |
|------|-----------|------|--------|
| `ui/survey_routing_data.json` | 2026-05-04 12:11 PM | 604,896 bytes | ❌ STALE |
| `output/survey_routing_data.json` | 2026-05-04 12:13 PM | 848,325 bytes | ✅ FRESH |

### Summary Statistics Comparison

| Metric | ui/ (STALE) | output/ (FRESH) | Expected | Match? |
|--------|-------------|-----------------|----------|--------|
| total_sites | 768 | 768 | 768 | ✅ |
| ready_to_assign | 553 | **661** | 661 | ❌ ui/ WRONG |
| review_required | 215 | **0** | 0 | ❌ ui/ WRONG |
| pending_scout | *(missing)* | **107** | 107 | ❌ ui/ MISSING |
| scout_submitted=True | 0 | **661** | 661 | ❌ ui/ WRONG |
| scout_submitted=False | 768 | **107** | 107 | ❌ ui/ WRONG |

### Schema Differences

**ui/ file (16 fields)** - OLD SCHEMA:
```
days_to_construction, notes, ready_to_assign, reason_for_decision,
schedule_status, scout_submitted, site, status, supplemental_flags,
survey_complete, survey_required, survey_type, upgrade_decision,
vendor, vendor_instructions, vues_submitted
```

**output/ file (24 fields)** - CURRENT SCHEMA:
```
assigned, assigned_vendor, days_to_construction, in_siteowl_design,
in_siteowl_installation, in_siteowl_live, notes, on_project_tracking,
passes_at_qa, percentage_complete, ready_to_assign, reason_for_decision,
schedule_status, scout_submitted, site, supplemental_flags, survey_complete,
survey_required, survey_returned_date, survey_returned_qa, survey_type,
upgrade_decision, vendor, vendor_instructions
```

**Missing fields in ui/ (10 fields):**
- assigned
- assigned_vendor
- in_siteowl_design
- in_siteowl_installation
- in_siteowl_live
- on_project_tracking
- passes_at_qa
- percentage_complete
- survey_returned_date
- survey_returned_qa

---

## Verification: evaluate_site() Function

**Location:** `C:\VUES\src\siteowlqa\survey_routing.py` (line 416)

**Logic Review:** ✅ CORRECT

The `evaluate_site()` function correctly implements the routing logic:

```python
# When scout is None (no scout submitted):
if scout is None:
    return SurveyRoutingRow(
        survey_required="PENDING",
        survey_type="PENDING",
        ready_to_assign="NO",
        scout_submitted=False,  # Correctly marked
    )

# When scout exists:
# ... (evaluation logic) ...
return SurveyRoutingRow(
    # ... (routing decisions) ...
    scout_submitted=True,  # Correctly marked
)
```

**Ready to Assign Logic:** ✅ CORRECT
```python
# RO-007 FIX: Site needs both a routing decision AND a vendor to be ready
if survey_required == "YES" and vendor:
    ready_to_assign = "YES"
elif survey_required == "NO":
    ready_to_assign = "YES"  # No survey needed, so "ready" is N/A
else:
    ready_to_assign = "NO"
```

---

## Verification: bake_data_into_html.py

**Location:** `C:\VUES\tools\bake_data_into_html.py`

**Sync Logic:** ✅ CORRECT (but not executed recently)

```python
def sync_data_from_output():
    """Copy fresh data from output/ to ui/ if output has newer files."""
    for fname in DATA_FILES.keys():
        output_file = OUTPUT_DIR / fname
        ui_file = UI_DIR / fname
        
        if output_file.exists():
            # Copy if ui file doesn't exist or output is newer
            if not ui_file.exists() or output_file.stat().st_mtime > ui_file.stat().st_mtime:
                shutil.copy2(output_file, ui_file)
```

**Issue:** This function should have copied `output/survey_routing_data.json` to `ui/` since output is newer (12:13 PM vs 12:11 PM), but it appears `bake_data_into_html.py` was NOT run after the fresh data was generated.

---

## Data Quality Verification

### output/survey_routing_data.json (FRESH - CORRECT)

✅ **661 sites with completed scouts ALL have:**
- `scout_submitted: true`
- `ready_to_assign: "YES"`
- Valid survey routing decision (YES/NO based on triggers)

✅ **107 sites without scouts ALL have:**
- `scout_submitted: false`
- `survey_required: "PENDING"`
- `survey_type: "PENDING"`
- `ready_to_assign: "NO"`
- `upgrade_decision: "AWAITING SCOUT"`

✅ **0 sites have survey_required: "REVIEW"**

### ui/survey_routing_data.json (STALE - INCORRECT)

❌ **ALL 768 sites incorrectly have:**
- `scout_submitted: false` (should be true for 661 sites)

❌ **215 sites incorrectly have:**
- `survey_required: "REVIEW"`
- `ready_to_assign: "NO"`

❌ **Missing pending_scout tracking in summary**

---

## Issues Identified

### Issue #1: Dashboard Displaying Stale Data
**Severity:** 🚨 CRITICAL  
**Impact:** All dashboard viewers see incorrect routing status  
**Root Cause:** `ui/survey_routing_data.json` not updated after fresh data generation

### Issue #2: bake_data_into_html.py Not Executed
**Severity:** ⚠️ HIGH  
**Impact:** Fresh data not synced to dashboard  
**Root Cause:** Manual step not performed after routing data refresh

### Issue #3: Schema Version Mismatch
**Severity:** ⚠️ HIGH  
**Impact:** Missing 10 tracking fields in dashboard  
**Root Cause:** ui/ file using old schema from prior data generation

---

## Fixes Required

### Fix #1: Sync Fresh Data to Dashboard (IMMEDIATE)
**Action:** Copy `output/survey_routing_data.json` to `ui/`

```powershell
Copy-Item "C:\VUES\output\survey_routing_data.json" "C:\VUES\ui\survey_routing_data.json" -Force
```

**Expected Result:**
- ui/ file updated to 848,325 bytes
- All 661 sites with scouts show ready_to_assign=YES
- All 107 sites without scouts show survey_required=PENDING
- 0 sites show survey_required=REVIEW

### Fix #2: Re-bake HTML with Fresh Data (IMMEDIATE)
**Action:** Run bake script to embed fresh data into HTML files

```powershell
cd C:\VUES
python tools\bake_data_into_html.py
```

**Expected Result:**
- All HTML files updated with fresh embedded data
- Dashboard works offline with correct data

### Fix #3: Verify Data Flow Process (RECOMMENDED)
**Action:** Document and enforce data flow:

1. Generate fresh routing data → writes to `output/survey_routing_data.json`
2. Run `tools/bake_data_into_html.py` → syncs to `ui/` and embeds in HTML
3. Verify dashboard shows correct data

---

## Validation Checklist

After applying fixes, verify:

- [ ] `ui/survey_routing_data.json` timestamp matches `output/`
- [ ] `ui/survey_routing_data.json` size = 848,325 bytes
- [ ] Dashboard summary shows ready_to_assign: 661
- [ ] Dashboard summary shows pending_scout: 107
- [ ] Dashboard summary shows review_required: 0
- [ ] Search dashboard for a PENDING site (e.g., site 1323)
- [ ] Verify site 1323 shows "AWAITING SCOUT"
- [ ] Search dashboard for a site with scout (e.g., site 1)
- [ ] Verify site 1 shows ready_to_assign: YES

---

## Conclusion

**Status:** The routing logic in `survey_routing.py` is CORRECT. The `evaluate_site()` function properly sets `ready_to_assign` based on scout completion and vendor assignment.

**Problem:** The dashboard is displaying STALE data because `ui/survey_routing_data.json` was not updated after fresh data was generated in `output/`.

**Solution:** Execute Fix #1 and Fix #2 immediately to sync fresh data to the dashboard.

**Prevention:** Ensure `tools/bake_data_into_html.py` is run after every routing data refresh as part of the deployment workflow.

---

**Audit performed by:** siteowlqa-dev-68e41b  
**Next Action:** Execute Fix #1 (copy fresh data) and Fix #2 (re-bake HTML)
