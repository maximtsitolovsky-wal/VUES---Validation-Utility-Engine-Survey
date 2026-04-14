# Agent: reviewer
**Category:** Session Role + Runtime Module  
**Type:** Prompt-defined persona (dev-time) + deterministic Python module (runtime)  
**Prompt Source:** `prompts/reviewer_prompt.md`  
**Runtime Module:** `src/siteowlqa/reviewer.py`  
**LLM Agent:** ❌ No — fully deterministic static analysis, no LLM call

---

## What It Is
The Reviewer exists at two levels:

1. **Session persona** — Code Puppy adopts this role to critically review code
   and pipeline runs during a dev session (guided by `prompts/reviewer_prompt.md`)

2. **Runtime module** — `reviewer.py` runs automatically after every submission,
   surfacing known risk patterns and contextual flags deterministically

Both use the same review criteria. The runtime module is the machine-speed implementation
of the same checklist the session persona applies manually.

## What It Reviews
| Area | What It Checks |
|---|---|
| Architecture | Module boundary violations |
| Business rules | Project ID overwrite, email rules (PASS omits score, FAIL includes score + CSV) |
| Concurrency | SubmissionRaw isolation, shared-state access |
| SQL safety | Parameter binding, injection risk |
| Null handling | Blank values handled without crash or unfair scoring |
| Config | Everything through `AppConfig`, no stray `os.getenv` |
| Secrets | No hardcoded credentials or tokens |
| Duplication | Same transformation in multiple places |
| Error handling | Exceptions caught at right level with right specificity |
| File size | Files growing beyond 600 lines |
| Naming | Functions and variables named clearly |

## Runtime Module: reviewer.py
- Called by `poll_airtable.py` after each submission completes
- Returns `ReviewResult` (status, risk_level, summary, issues, recommended_fixes)
- Surfaces `_KNOWN_RISK_PATTERNS` on every run — they stay visible until resolved
- Enriches with memory warnings from the lesson archive
- Performs static analysis of module source on demand (`review_code_module`)

## Known Risk Patterns Flagged on Every Run
| ID | Name | Severity |
|---|---|---|
| RISK-001 | SubmissionRaw Isolation (RESOLVED) | INFO |
| RISK-002 | Project ID Overwrite Not Verified Post-Insert | MEDIUM |
| RISK-003 | Airtable Attachment URL Expiry | LOW |
| RISK-004 | PASS Email Omits Score (by design) | INFO |
| RISK-005 | Blank NULL Handling in SQL Insert | MEDIUM |

## Output Format (ReviewResult)
```
status:            APPROVED | APPROVED_WITH_WARNINGS | REJECTED
risk_level:        LOW | MEDIUM | HIGH | CRITICAL
summary:           one-line submission summary
issues:            list[ReviewIssue] with severity, type, detail
recommended_fixes: list of actionable strings
```

## Rule: Never Fixes, Only Surfaces
The Reviewer does not fix code — that's the Generator + archive/memory feedback loop.
It identifies. Everything else stays in its lane.
