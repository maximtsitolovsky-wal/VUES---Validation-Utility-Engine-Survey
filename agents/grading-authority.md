# Agent: grading-authority
**Category:** Session Role + Runtime Logic  
**Type:** Prompt-defined grading canon + deterministic Python implementation  
**Prompt Source:** `prompts/grading_prompt.md`  
**Runtime Modules:** `src/siteowlqa/python_grader.py`, `src/siteowlqa/poll_airtable.py`  
**LLM Agent:** ❌ No — grading is 100% deterministic. LLM is NOT on the grading critical path.

---

## What It Is
The Grading Authority defines the canonical, deterministic rules for assigning
PASS / FAIL / ERROR to every submission. This is the most important set of rules
in the project — they must never be fudged, softened, or reinterpreted.

The prompt in `prompts/grading_prompt.md` is the constitution. `python_grader.py`
is the implementation. When they conflict, fix the implementation — not the constitution.

## The Three Valid Outcomes
| Status | When | Score | Reason |
|---|---|---|---|
| PASS | File loaded + eligible + matches reference ≥95.0% | 100.0 | Empty or brief informational note |
| FAIL | File loaded + eligible + matches reference <95.0% | Numeric % <95 | Mismatch summary from evidence |
| ERROR | Any condition preventing reliable grading | null | Explanatory error message |

## The Authority Order (never skip a step)
1. File load outcome
2. Structural eligibility for grading
3. Python comparison against site-scoped reference rows
4. Output normalization rules

## Pass Threshold
- Official threshold: **95.0%**
- PASS reporting score is always normalized to **100.0**
- FAIL ≥95.0 is **invalid** → must become ERROR
- PASS with numeric score <95.0 is **invalid** → must become ERROR
- ERROR disguised as 0% FAIL is **invalid** → must be ERROR

## What the Grading System May and May Not Do

**MAY:**
- Load files, normalize inputs, validate eligibility
- Fetch reference rows from SQL Server
- Compare submission rows against the reference set
- Assign PASS / FAIL / ERROR and numeric FAIL scores
- Format output and write to Airtable

**MAY NOT:**
- Invent reference rows that do not exist
- Ignore structural errors
- Convert ERROR → PASS or ERROR → FAIL
- Convert FAIL → PASS without matching evidence
- Fabricate mismatch counts or reasons

## Structural Invalidity → Always ERROR
A submission is structurally invalid (and must ERROR) if:
- File cannot be parsed or loaded
- Critical columns missing in a way preventing fair grading
- No reference rows exist for the site
- Required keys for row matching are absent or unusable
- Any schema defect makes grading unreliable or misleading

> Row-count mismatch alone is NOT an automatic ERROR — it becomes evidence that may lead to FAIL after comparison runs.

## Source of Truth Boundaries
| What | Source of Truth |
|---|---|
| Graded outcomes | Python (`python_grader.py`) |
| Site reference rows | SQL Server (`ReferenceExport` view) |
| Vendor email delivery | Airtable automation (zero SMTP in pipeline) |

## Implementation Modules
| Module | Role |
|---|---|
| `python_grader.py` | Core comparison logic — canonical-header matching |
| `poll_airtable.py` | Orchestrates per-record grading pipeline |
| `sql.py` | Fetches site-scoped reference rows |
| `file_processor.py` | Loads and normalizes the vendor file |
| `models.py` | `GradingResult`, `SubmissionStatus`, shared types |
