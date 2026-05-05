# INTEGRITY AUDIT REPORT — VUES Survey Routing Re-Audit
**Audit ID:** integrity-marshal-ff7ba2  
**Audit Date:** 2026-05-05T08:35:39 (Walmart CT)  
**Scope:** Post-fix re-audit of 5 VUES routing files at C:\VUES\ui\  
**Auditor:** Integrity Marshal 🛡️ (integrity-marshal-ff7ba2)

---

## OVERALL VERDICT: PARTIAL
## SEVERITY: HIGH

4 of 5 files PASS. `routing.html` FAILS — residual Techwise/SAS vendor options remain in filter dropdowns.

---

## FILE-BY-FILE VERDICTS

| File | Verdict | Severity | Key Issue |
|------|---------|----------|-----------|
| routing.html | ❌ FAIL | HIGH | Techwise + SAS still in 4 dropdown menus |
| vendor_locations.json | ✅ PASS | NONE | Clean; math verified |
| globe.html | ⚠️ PARTIAL | LOW | 1-site Wachter discrepancy; no timestamp |
| vues_metrics_current.json | ✅ PASS | NONE | Clean; fresh timestamp confirmed |
| survey_routing_data.json | ✅ PASS | LOW | Surveys_complete minor gap (63 vs 50) |

---

## DETAILED FINDINGS TABLE

| # | File | Category | Finding | Severity |
|---|------|----------|---------|----------|
| 1 | routing.html | Vendor Residue | `<option value="Techwise">` + `<option value="SAS">` present in 4 separate dropdown menus (upgrade, nosurvey, scout, completed sections) | HIGH |
| 2 | routing.html | Text Fix | "No scout submission" removed ✓; Legend shows correct `reason = "Scout not submitted"` | NONE |
| 3 | vendor_locations.json | Vendor Check | Zero Techwise/SAS references. Only CEI/Wachter/Everon present | NONE |
| 4 | vendor_locations.json | CEI Math | CEI marker sum verified: IL(7)+KY(5)+CA(21)+NM(1)+TX(69)+AR(21)+OK(20)+GA(23)+FL(52)+AL(22)+KS(19)+AZ(18)+TN(22)+MS(12)+MO(15)+LA(15)+WV(7)+NC(33)+SC(14)+VA(18)+MD(13)+DC(1) = **428** ✓ matches vendor_totals.CEI | NONE |
| 5 | vendor_locations.json | Wachter Math | Sum = 176 ✓; Everon sum = 154 ✓ | NONE |
| 6 | globe.html | Vendor Check | Zero Techwise/SAS in scoutData or surveyData hardcoded blocks | NONE |
| 7 | globe.html | Wachter Discrepancy | Wachter survey_required = 144 in globe.html vs 145 in survey_routing_data.json (1-site gap) | LOW |
| 8 | globe.html | Timestamp | No embedded generated_at; cannot independently verify freshness | LOW |
| 9 | vues_metrics_current.json | Timestamp | generated_at = "2026-05-05T08:35:22" ✓ confirmed today | NONE |
| 10 | vues_metrics_current.json | CEI Count | scout.by_vendor.CEI = 436 ✓ within expected 425-436 range | NONE |
| 11 | vues_metrics_current.json | Math | Scout total: 172+118+436+3 = 729 ✓; Survey+Scout = 70+729 = 799 ✓ | NONE |
| 12 | survey_routing_data.json | Timestamp | generated_at = "2026-05-05T08:32:59" ✓ confirmed today | NONE |
| 13 | survey_routing_data.json | Pending Scout | pending_scout = 89 ✓ within expected 89-90 range | NONE |
| 14 | survey_routing_data.json | CEI Count | vendor_breakdown.CEI.total = 425 ✓ within expected range | NONE |
| 15 | survey_routing_data.json | Site Math | 425+150+188+6 = 769 ✓ matches total_sites | NONE |
| 16 | survey_routing_data.json | Survey Math | Surveys required: 414+94+145+1 = 654 ✓ matches surveys_required | NONE |
| 17 | survey_routing_data.json | Complete Gap | surveys_complete summary = 63; vendor breakdown complete sums = 21+11+18+0 = **50** (13-site gap, likely cross-vendor assignment routing) | LOW |

---

## COMPLIANCE SECTIONS

### 🧠 MEMORY COMPLIANCE
- No cross-session memory claims made. All data verified from live file reads this session. COMPLIANT.

### 📡 LIVE DATA COMPLIANCE
- vues_metrics_current.json: timestamp 2026-05-05T08:35:22 — generated 3 minutes before audit start. FRESH ✓
- survey_routing_data.json: timestamp 2026-05-05T08:32:59 — generated ~7 minutes before audit start. FRESH ✓
- vendor_locations.json: no timestamp. Cannot confirm freshness. Classified as **last-known / unverifiable date**.
- globe.html: no timestamp. Cannot confirm freshness. Classified as **last-known / unverifiable date**.
- routing.html: no timestamp. Cannot confirm freshness. Classified as **last-known / unverifiable date**.

### ✅ TRUTHFULNESS COMPLIANCE
- Claim "No Techwise or SAS in vendor totals": PARTIALLY FALSE — Techwise/SAS removed from all JSON data files but still present as UI dropdown `<option>` entries in routing.html
- Claim "CEI ~425-436": VERIFIED — 425 (routing JSON), 428 (locations/globe), 436 (metrics) ✓
- Claim "Awaiting Scout ~89-90": VERIFIED — pending_scout = 89 ✓
- Claim "files freshly generated today": PARTIAL — only 2 of 5 files have verifiable timestamps

### 🏁 COMPLETION COMPLIANCE
- Fix #1 (routing.html "Scout not submitted" text): PARTIAL — old text removed ✓, correct text in legend ✓, but Techwise/SAS dropdown options not cleaned
- Fix #2 (vendor_locations.json CEI merge): COMPLETE ✓
- Fix #3 (globe.html hardcoded data): COMPLETE ✓ (minor 1-site Wachter rounding gap)
- Fix #4 (vues_metrics_current.json regeneration): COMPLETE ✓
- Fix #5 (survey_routing_data.json regeneration): COMPLETE ✓

---

## REPAIR ORDERS

[ ] RO-001 [HIGH] routing.html — Remove `<option value="Techwise">Techwise</option>` and `<option value="SAS">SAS</option>` from ALL 4 vendor filter dropdowns: upgrade section, nosurvey section, scout section, completed section. These options present defunct vendors as valid filter choices in the UI.

[ ] RO-002 [LOW] globe.html — Reconcile Wachter survey_required: globe.html shows 144, survey_routing_data.json shows 145. Confirm which is authoritative and sync the hardcoded value.

[ ] RO-003 [LOW] survey_routing_data.json — Investigate surveys_complete discrepancy: summary field = 63, vendor breakdown complete sum = 50 (gap of 13). If due to cross-vendor assignment routing, add an explanatory field. If a calculation bug, fix the generator.

[ ] RO-004 [INFO] vendor_locations.json, globe.html, routing.html — Consider adding a generated_at field or comment to static/HTML files to allow future freshness verification.

---

## MEMORY UPDATE REQUIREMENTS

- No memory corrections required. No stale memory claims were detected.
- Record for this session: routing.html contains residual Techwise/SAS UI dropdown options as of 2026-05-05T08:35.

---

## CEI COUNT CROSS-FILE SUMMARY (for reference)

| Source File | CEI Value | Context |
|-------------|-----------|---------|
| survey_routing_data.json | 425 | Routing assignment slots |
| vendor_locations.json | 428 | Geographic marker pins |
| globe.html (hardcoded) | 428 | Matches vendor_locations.json ✓ |
| vues_metrics_current.json | 436 | Scout submission records |
| **Expected range (user-stated)** | **425-436** | ✅ All within tolerance |

---

## FINAL INSTRUCTION

**To operator / development team:**

routing.html requires a targeted fix before it can be considered fully remediated. The data layer (JSONs) is clean — Techwise and SAS have been successfully purged from all data files. However, the UI layer still presents these defunct vendors as selectable filter options in four separate dropdown menus. Any user selecting "Techwise" or "SAS" from these dropdowns will receive zero results, which creates a confusing UX and signals an incomplete integration of the vendor consolidation.

**Action required:**
1. Open `C:\VUES\ui\routing.html`
2. Search for all `<option value="Techwise">` and `<option value="SAS">` tags
3. Remove all 4 occurrences (upgrade, nosurvey, scout, completed sections)
4. Optionally re-run this audit to confirm PASS

All other files are compliant. The system is operationally sound with CEI counts consolidated and scout counts accurate.
