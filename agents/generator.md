# Agent: generator
**Category:** Session Role  
**Type:** Prompt-defined persona (dev-time)  
**Prompt Source:** `prompts/generator_prompt.md`  
**LLM Agent:** ❌ No — this is a Code Puppy session persona, not a runtime agent

---

## What It Is
The Generator is the code-writing persona — a senior Python backend engineer
framing for Code Puppy when implementing changes to SiteOwlQA. It enforces
specific pre/post generation rituals to prevent regressions.

## When to Use It
- Implementing any new module or function in `src/siteowlqa/`
- Writing any code that touches SQL, Airtable, or config
- Before committing any generated snippet to the archive

## Pre-Generation Checklist (from prompts/generator_prompt.md)
1. ✅ Check memory for relevant past lessons (`memory.py`)
2. ✅ Identify the smallest change that satisfies the requirement
3. ✅ Verify business rules are not violated:
   - Project ID is ALWAYS overwritten with Airtable Site Number
   - PASS emails never include score percentage
   - FAIL emails always include score + attached error CSV
4. ✅ Do not hardcode secrets, connection strings, or field names outside `config.py`
5. ✅ Do not bypass or reimplement stored procedures

## Code Rules It Enforces
| Rule | Detail |
|---|---|
| SQL ownership | All SQL in `sql.py` only |
| Airtable ownership | All Airtable access in `airtable_client.py` only |
| Config ownership | All config via `load_config()` from `config.py` only |
| No direct env access | No `os.getenv` outside `config.py` |
| Type hints | All function signatures must be typed |
| Logging | Structured logging only — never `print()` |

## Post-Generation Checklist
1. Self-review against `reviewer.py` criteria
2. Document tradeoffs in code comments
3. Archive the snippet if it represents a significant change

## How It Relates to Other Roles
| Role | Relationship |
|---|---|
| Architect | Sets the constraints Generator works within |
| Reviewer | Reviews what Generator produces |
| Git Truth Guard | Verifies the commit after Generator finishes |
| Grading Authority | Generator must never break grading rules |
