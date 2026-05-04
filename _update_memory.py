#!/usr/bin/env python
"""Prepend the new issue to MEMORY.md"""

new_entry = """### 2026-05-04 — CRITICAL: Techwise & SAS Filtered Out of Survey Routing Decision Tree

**Issue:** Vendor routing decision tree (`src/siteowlqa/survey_routing.py`, line 45) only accepts 3 vendors: `{"Wachter", "CEI", "Everon"}`. **Techwise (78 sites) and SAS (8 sites) are completely filtered out** by `_normalize_vendor()` function.

**Current Status:**
- ✅ **Tracked**: Both vendors appear in assignment system (5 Excel sheets: Wachter, Techwise, SAS, Everon, CEI = 758 total sites)
- ✅ **Visible**: Both vendors shown in dashboards (vendor pills, leaderboards)
- ❌ **NOT routed**: Techwise & SAS sites get decision tree output "PENDING" → never enter routing pipeline
- ❌ **No survey assignment**: 86 sites (78 Techwise + 8 SAS) excluded from vendor survey routing

**Root Cause:** `VALID_SURVEY_VENDORS` set hardcoded to 3 vendors. Likely historical—only these 3 were survey-capable at design time.

**Evidence:** Generated `CEI_Survey_Report.xlsx` on 2026-05-04. Shows 342 CEI sites with proper decision tree evaluation (BOTH/CCTV/FA/INTRUSION/NONE). Techwise/SAS cannot be processed through same logic.

**Decision Required:**
- **Option A**: Add Techwise & SAS to `VALID_SURVEY_VENDORS` (assumes they do surveys)
- **Option B**: Document as assignment-only vendors; remove from survey routing
- **Option C**: Remove from assignment tracking entirely

**Scope:** `survey_routing.py::_normalize_vendor()` + downstream filters on `VALID_SURVEY_VENDORS`

**Artifacts Generated:**
- `CEI_Survey_Report.xlsx` — 342 CEI sites with survey types determined by decision tree
- `scripts/generate_cei_survey_report.py` — Tool to generate vendor-specific reports

**Status:** OPEN — awaiting decision on Techwise/SAS survey scope.

"""

with open("MEMORY_original.txt", "r", encoding="utf-8") as f:
    original = f.read()

with open("MEMORY.md", "w", encoding="utf-8") as f:
    f.write(new_entry)
    f.write(original)

print("✅ MEMORY.md updated with new issue entry at top")
