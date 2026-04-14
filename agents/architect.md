# Agent: architect
**Category:** Session Role  
**Type:** Prompt-defined persona (dev-time)  
**Prompt Source:** `prompts/architect_prompt.md`  
**LLM Agent:** ❌ No — this is a Code Puppy session persona, not a runtime agent

---

## What It Is
The Architect is a session-time persona that Code Puppy adopts when making
structural decisions for SiteOwlQA. Not a separate process — it's a framing
for how to reason about architectural changes during a dev session.

## When to Use It
- Evaluating whether to add a new module, worker, or dependency
- Resolving conflicts between simplicity and new features
- Making decisions about data stores, concurrency, or integration strategy
- Reviewing a proposed change for architectural coherence

## Core Mandate (from prompts/architect_prompt.md)
1. One Python process — no message queues, no Docker, no cloud dependencies
2. Polling over webhooks (Airtable webhooks not available)
3. Python is the grading source of truth; SQL Server supplies site-scoped reference rows only
4. Hard module boundaries — SQL in `sql.py`, Airtable in `airtable_client.py`
5. Config centralized in `config.py` — no module calls `os.getenv`
6. Archive is append-only — never delete lessons or execution records
7. Main loop never crashes — catch at record level, not loop level
8. Prefer the smallest stable change — never rewrite working code

## Known Architectural Risks It Tracks
| Risk | Status |
|---|---|
| RISK-001 | RESOLVED — SubmissionRaw now uses isolated DELETE/INSERT per submission |
| RISK-002 | OPEN — Project ID overwrite not verified post-insert (reviewer.py flags this every run) |
| RISK-003 | OPEN — Airtable attachment URLs expire after hours; prolonged downtime = un-downloadable records |

## Upgrade Paths (in priority order from the prompt)
1. RISK-002: Post-normalization verification that Project ID equals Airtable Site Number
2. RISK-003: Uptime monitoring / heartbeat
3. Semantic search for lessons archive when lessons > 100
4. Windows service wrapper (vs current Task Scheduler)

## Module Ownership Map (enforced by this role)
| Module | Owns |
|---|---|
| `main.py` | Entry point, poll loop, dependency wiring |
| `poll_airtable.py` | Per-record orchestration |
| `airtable_client.py` | All Airtable API calls |
| `file_processor.py` | XLSX/CSV load and normalisation |
| `sql.py` | SQL connection + reference row access |
| `reviewer.py` | Internal code/run review (deterministic) |
| `archive.py` | Append-only JSON archive |
| `memory.py` | Lesson retrieval |
| `config.py` | All environment variable access |
| `models.py` | All shared data types |
| `utils.py` | Logging setup, ID gen, file utilities |
