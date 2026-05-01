# Integrity Audit — Vendor Name Mappings in ui/analytics.html
**Auditor:** integrity-marshal-d0f46c  
**Timestamp:** 2026-05-01T12:49:45 (Walmart Central Time)  
**Scope:** `ui/analytics.html` → `VENDOR_SHORT` map + backing data `ui/vues_metrics_current.json`  
**Evidence gathered via:** `read_file`, `grep` — all findings are directly observed, not inferred.

---

## VENDOR_SHORT map (analytics.html) — Raw Findings

| Key (lowercased input) | Mapped Output | Status |
|---|---|---|
| `custom electronics` | `'CE'` | ❌ WRONG — must be `'CEI'` |
| `custom electronics inc` | `'CE'` | ❌ WRONG — must be `'CEI'` |
| `everon` | `'Everon'` | ✅ Correct |
| `everon solutions` | `'Everon'` | ✅ Correct |
| `techwise is` | `'TechWise'` | ⚠️ Key is garbled raw form; display should be `'Techwise'` |
| `techwise` | `'TechWise'` | ⚠️ Capitalization wrong — should be `'Techwise'` |
| `wachter` | `'Wachter'` | ✅ Correct |
| `safe & sound security` | `'S&S'` | ❌ WRONG — must be `'SAS'` |
| `safe and sound security` | `'S&S'` | ❌ WRONG — must be `'SAS'` |
| `safe & sound` | `'S&S'` | ❌ WRONG — must be `'SAS'` |
| `convergint` | `'Convergint'` | ❓ UNVERIFIED — not in approved vendor list |
| `convergint technologies` | `'Convergint'` | ❓ UNVERIFIED — not in approved vendor list |
| `securitas` | `'Securitas'` | ❓ UNVERIFIED — not in approved vendor list |
| `johnson controls` | `'JCI'` | ❓ UNVERIFIED — not in approved vendor list |
| `jci` | `'JCI'` | ❓ UNVERIFIED — not in approved vendor list |
| `stanley security` | `'Stanley'` | ❓ UNVERIFIED — not in approved vendor list |
| `adt` | `'ADT'` | ❓ UNVERIFIED — not in approved vendor list |
| `unknown` | `'Unknown'` | ✅ Neutral/acceptable |

## vues_metrics_current.json (data source) — Raw Findings

| Raw Key in JSON | Records | Status |
|---|---|---|
| `Everon` | 80 | ✅ Correct |
| `Wachter` | 69 | ✅ Correct |
| `Customelectronics` | 345 | ❌ WRONG — should be `CEI` |
| `Techwiseis` | 73 | ❌ WRONG (typo) — should be `Techwise` |
| `Techwisis` | 1 | ❌ WRONG (typo) — should be `Techwise` |
| `Gmail` | 2 | 🚨 FABRICATED/ERRONEOUS — Gmail is not a vendor |
| `Safeandsoundsecurity` | 9 | ❌ WRONG — should be `SAS` |

---

## INTEGRITY AUDIT REPORT

```
═══════════════════════════════════════════════════════════════
                    INTEGRITY AUDIT REPORT
═══════════════════════════════════════════════════════════════

📋 VERDICT: FAIL
⚠️  SEVERITY: BLOCKER

───────────────────────────────────────────────────────────────
                         FINDINGS
───────────────────────────────────────────────────────────────
| #  | Category           | Finding                                            | Severity |
|----|--------------------|----------------------------------------------------|----------|
| 1  | Incorrect Mapping  | 'custom electronics' → 'CE' (must be 'CEI')        | HIGH     |
| 2  | Incorrect Mapping  | 'custom electronics inc' → 'CE' (must be 'CEI')    | HIGH     |
| 3  | Incorrect Mapping  | 'safe & sound security' → 'S&S' (must be 'SAS')   | HIGH     |
| 4  | Incorrect Mapping  | 'safe and sound security' → 'S&S' (must be 'SAS') | HIGH     |
| 5  | Incorrect Mapping  | 'safe & sound' → 'S&S' (must be 'SAS')            | HIGH     |
| 6  | Wrong Casing       | 'techwise' → 'TechWise' (must be 'Techwise')       | MEDIUM   |
| 7  | Garbled Key        | 'techwise is' key is corrupted raw form of vendor  | MEDIUM   |
| 8  | Unverified Entry   | 'convergint'/'convergint technologies' not in list | MEDIUM   |
| 9  | Unverified Entry   | 'securitas' not in approved vendor list            | MEDIUM   |
| 10 | Unverified Entry   | 'johnson controls'/'jci' not in approved list      | MEDIUM   |
| 11 | Unverified Entry   | 'stanley security' not in approved vendor list     | MEDIUM   |
| 12 | Unverified Entry   | 'adt' not in approved vendor list                  | MEDIUM   |
| 13 | Data Corruption    | JSON key "Customelectronics" (345 records)         | HIGH     |
| 14 | Data Corruption    | JSON key "Techwiseis" (73 records, typo)           | HIGH     |
| 15 | Data Corruption    | JSON key "Techwisis" (1 record, typo)              | HIGH     |
| 16 | Data Corruption    | JSON key "Safeandsoundsecurity" (9 records)        | HIGH     |
| 17 | FABRICATED VENDOR  | JSON key "Gmail" — 2 records assigned to Gmail     | BLOCKER  |

───────────────────────────────────────────────────────────────
                    COMPLIANCE SECTIONS
───────────────────────────────────────────────────────────────

🧠 MEMORY COMPLIANCE:
   - N/A — no memory claims made by this component.

📡 LIVE DATA COMPLIANCE:
   - vues_metrics_current.json contains corrupted/garbled vendor
     keys that are being presented as live metrics data.
     "Gmail" is surfaced as a vendor in live dashboards — FAIL.

✅ TRUTHFULNESS COMPLIANCE:
   - VENDOR_SHORT map outputs 'CE' for CEI — factually wrong label,
     misrepresents the vendor in all rendered UI.
   - VENDOR_SHORT map outputs 'S&S' for SAS — factually wrong label.
   - 'TechWise' vs 'Techwise' — minor casing misrepresentation.
   - 5 vendor entries (Convergint, Securitas, JCI, Stanley, ADT) have
     no authoritative backing in the provided approved vendor list.
     Cannot be confirmed as real project vendors without external
     verification. Flagged as UNVERIFIED, not confirmed fabricated.
   - "Gmail" in vues_metrics_current.json is a CONFIRMED fabricated
     vendor entry — Gmail is an email provider, not a security vendor.

🏁 COMPLETION COMPLIANCE:
   - The vendor mapping logic in analytics.html is incomplete and
     incorrect. CE/S&S labels will display in charts and tables
     instead of CEI/SAS. Any dashboard output showing these labels
     is misleading and should not be considered complete or correct.

───────────────────────────────────────────────────────────────
                      REPAIR ORDERS
───────────────────────────────────────────────────────────────
[ ] RO-001: In analytics.html VENDOR_SHORT — change all 'CE' values
            to 'CEI' (affects keys: 'custom electronics',
            'custom electronics inc')

[ ] RO-002: In analytics.html VENDOR_SHORT — change all 'S&S' values
            to 'SAS' (affects keys: 'safe & sound security',
            'safe and sound security', 'safe & sound')

[ ] RO-003: In analytics.html VENDOR_SHORT — change 'TechWise' to
            'Techwise' on both 'techwise' and 'techwise is' keys.
            Also evaluate whether 'techwise is' key is the correct
            raw form or if it was introduced by the "Techwiseis"
            data corruption in the JSON source.

[ ] RO-004: In analytics.html VENDOR_SHORT — confirm or remove the
            5 unverified vendor entries (Convergint, Securitas,
            Johnson Controls/JCI, Stanley Security, ADT) with a
            product owner. If not real project vendors, remove them.

[ ] RO-005: In vues_metrics_current.json — correct "Customelectronics"
            key to "CEI" (345 records affected). Investigate upstream
            source (email normalization pipeline) that emits this value.

[ ] RO-006: In vues_metrics_current.json — merge "Techwiseis" (73)
            and "Techwisis" (1) into "Techwise". Investigate source
            pipeline for the garbling of vendor email domain parsing.

[ ] RO-007: In vues_metrics_current.json — merge "Safeandsoundsecurity"
            (9 records) into "SAS".

[ ] RO-008: BLOCKER — Investigate and remove "Gmail" as a vendor key
            in vues_metrics_current.json (2 records). These records
            likely have vendor_email set to a @gmail.com address and
            the pipeline incorrectly used the email domain as the vendor
            name. Reprocess or manually correct those 2 records.

───────────────────────────────────────────────────────────────
                   MEMORY UPDATE REQUIREMENTS
───────────────────────────────────────────────────────────────
- MEMORY.md should record: Approved vendor shorthand list =
  CEI, Wachter, Everon, SAS, Techwise. Any pipeline normalization
  of vendor names must resolve to these canonical forms.
- MEMORY.md should record: "Gmail" is not a vendor. If vendor_email
  domain parsing is used to derive vendor_name, @gmail.com addresses
  must be flagged as UNKNOWN or investigated, not mapped to "Gmail".

───────────────────────────────────────────────────────────────
                    FINAL INSTRUCTION
───────────────────────────────────────────────────────────────
DO NOT ship or present any dashboard output until RO-001, RO-002,
and RO-008 are resolved. The 'CE' / 'S&S' labels are actively
misrepresenting vendor identities on live dashboards. The "Gmail"
entry is a data integrity blocker — 2 records are assigned to a
fabricated vendor and will skew all vendor-level metrics.

Operator: apply all 8 Repair Orders in sequence, regenerate
vues_metrics_current.json from the corrected pipeline, then
re-audit before promoting to production.

═══════════════════════════════════════════════════════════════
```
