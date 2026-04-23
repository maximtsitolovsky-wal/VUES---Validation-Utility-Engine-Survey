# VUES Grading Architecture

## Survey Type Routing

The `Survey Type` column in Airtable determines which grading logic is applied to each submission.

```
                    ┌─────────────────┐
                    │  Airtable       │
                    │  Survey Type    │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │    CCTV      │  │ FA/Intrusion │  │    BOTH      │
    │              │  │              │  │  (Default)   │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ Filter: rows │  │ Filter: rows │  │ No filtering │
    │ WITHOUT      │  │ WITH         │  │ All rows     │
    │ Abbrev/Desc  │  │ Abbrev/Desc  │  │              │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ 6 Columns    │  │ 2-3 Columns  │  │ 8 Columns    │
    │ No Post-Pass │  │ No Post-Pass │  │ + Post-Pass  │
    └──────────────┘  └──────────────┘  └──────────────┘
```

---

## Row Filtering by Survey Type

A single submission may contain both CCTV devices (cameras) and FA/Intrusion devices (panels). To avoid overlap, rows are filtered before grading:

| Survey Type | Row Filter | Rows Included |
|-------------|------------|---------------|
| **CCTV** | Abbreviated Name AND Description are empty | Camera/video equipment only |
| **FA/Intrusion** | Abbreviated Name OR Description have content | Fire alarm/intrusion panels only |
| **BOTH** | No filter | All rows |

---

## Grading Columns by Survey Type

### CCTV
Grades camera/video equipment fields:
| Column | Description |
|--------|-------------|
| Name | Device name |
| Part Number | Equipment part number |
| Manufacturer | Equipment manufacturer |
| IP Address | Network IP address |
| MAC Address | Hardware MAC address |
| IP / Analog | Connection type |

**Post-Pass Correction:** ❌ No

---

### FA/Intrusion (Fire Alarm / Intrusion)
Grades fire and intrusion panel fields:
| Column | Description |
|--------|-------------|
| Abbreviated Name | Short device identifier |
| Description | Device description |
| Name | Device name (conditional*) |

*\*Name is only graded if Abbreviated Name has content in the submission*

**Post-Pass Correction:** ❌ No

---

### BOTH (Default / Original Logic)
Grades ALL fields — combines CCTV + FA/Intrusion:
| Column | Description |
|--------|-------------|
| Name | Device name |
| Abbreviated Name | Short device identifier |
| Part Number | Equipment part number |
| Manufacturer | Equipment manufacturer |
| IP Address | Network IP address |
| MAC Address | Hardware MAC address |
| IP / Analog | Connection type |
| Description | Device description |

**Post-Pass Correction:** ✅ Yes

---

## Airtable Configuration

**Column Name:** `Survey Type`  
**Field Type:** Single Select  
**Options:**
- `CCTV`
- `FA/Intrusion`
- `BOTH`

**Default Behavior:** If Survey Type is empty or unrecognized, defaults to `BOTH` for backward compatibility.

---

## Code References

| File | Purpose |
|------|---------|
| `src/siteowlqa/config.py` | Survey type constants, grading column definitions |
| `src/siteowlqa/python_grader.py` | Grading logic with survey type routing |
| `src/siteowlqa/poll_airtable.py` | Main processing with conditional post-pass |
| `src/siteowlqa/models.py` | AirtableRecord with survey_type field |

---

## Pass/Fail Threshold

All survey types use the same pass/fail threshold:
- **PASS:** Score ≥ 95%
- **FAIL:** Score < 95%

The score is calculated as: `(matched_rows / reference_rows) × 100`

---

*Last updated: April 2026*
