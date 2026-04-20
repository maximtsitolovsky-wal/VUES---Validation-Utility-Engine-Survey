# AGENT.md — SiteOwlQA Relentless Memory Agent
> Behavior spec. Read before operating. Not a tutorial — a ruleset.

---

## Identity

The Relentless Memory Agent is not a separate process.
It is a **behavioral layer** that any agent (Code Puppy or otherwise) running
inside `C:\VUES` must embody.

Its job: capture broadly, store selectively, compress aggressively, recall minimally.
Its metric: token cost reduction over repeated sessions without losing continuity.

---

## Environment — Hard Assumptions (Never Re-Derive)

| Property              | Value                                              |
|-----------------------|----------------------------------------------------|
| OS                    | Windows 11 Enterprise — no WSL assumed             |
| Working dir           | `C:\VUES`                                 |
| Runtime               | Python 3.x, single-process, no Docker              |
| Package layout        | `src/siteowlqa/` — imports use `siteowlqa.*`       |
| Entry point           | `main.py` → `siteowlqa.main.run_forever()`         |
| Deployment            | Windows Task Scheduler (logon + 90s delay)         |
| Credential store      | `~/.siteowlqa/config.json` — NOT `.env`            |
| Config owner          | `config.py` — the ONLY caller of `os.getenv`       |
| Package manager       | `uv` preferred                                     |
| Git                   | Available. Commit after every completed change.    |
| Docker                | Not installed. Never assume it.                    |

These are not preferences. They are facts. Do not re-derive them from scratch.

---

## Memory Surfaces — Recognized and Authoritative

The agent treats these files as explicit memory. Nothing outside this list
is assumed to persist between sessions:

| Surface           | Role                                                   |
|-------------------|--------------------------------------------------------|
| `MEMORY.md`       | Durable decision log — primary write target            |
| `CLAUDE.md`       | Session protocol + governance rules                    |
| `README.md`       | Project overview — stable reference                    |
| `development.md`  | Roadmap, delivery tracking                             |
| `INFRA.md`        | System/build snapshot                                  |
| `prompts/`        | LLM prompt templates                                   |
| `skills/INDEX.md` | Skill registry — check before every task               |
| `skills/*.md`     | Individual skill playbooks                             |
| `docs/`           | Extended documentation                                 |
| `tests/`          | Test evidence — authoritative for runtime truth        |
| Memory backend    | `docs/memory-agent/store/` — see `MEMORY_BACKEND_SPEC.md` |

**No hidden persistence exists beyond these surfaces.**
If it is not in one of these files, the agent does not know it.

---

## Session Operating Protocol

This agent extends — does not replace — the CLAUDE.md session protocol.
The CLAUDE.md 5-step loop (READ → PROVE → SKILLS → EXECUTE → REMEMBER → EXTRACT)
remains the outer loop.

The memory agent behavior inserts at these points:

```
CLAUDE Step 1 (READ MEMORY.md)
  └─ Memory agent: also scan session store for relevant tags
     Retrieve ≤5 expanded notes, ≤800 tokens total

CLAUDE Step 3 (EXECUTE)
  └─ Memory agent: append session notes as work progresses
     Compact. One note per meaningful event.

CLAUDE Step 4 (WRITE to MEMORY.md)
  └─ Memory agent: evaluate session notes for durable promotion
     Promote only what survives the promotion gate (see MEMORY_POLICY.md)
     Compress before writing.

CLAUDE Step 5 (EXTRACT skill)
  └─ Memory agent: emit handoff block if session is ending
     (see HANDOFF_SPEC.md)
```

---

## What the Agent Observes

Observe broadly. Note selectively.

**Always watch for:**
- User goals, constraints, non-goals stated during the session
- File/module changes made and why
- Decisions with rationale (especially ones that took effort to reach)
- Failures, root causes, and verified fixes
- Tests that passed or failed and what they proved
- Assumptions that turned out to be wrong
- Open loops left unresolved at session end
- Patterns that will repeat

**SiteOwlQA-specific signals to always capture:**
- Anything touching Windows Task Scheduler behavior or launch path
- Changes to `main.py` / `siteowlqa.main.run_forever()` semantics
- `src/` import path issues or resolution
- `~/.siteowlqa/config.json` credential changes
- Airtable API decisions (Survey: `apptK6zNN0Hf3OuoJ`, Scout: `appAwgaX89x0JxG3Z`)
- Archive append behavior (append-only — never delete)
- Dashboard template vs. served output distinction
- SQL Server reference row assumptions
- RISK-002 or RISK-003 progress
- `memory.py` lesson retrieval changes

---

## What the Agent Does NOT Store by Default

- Raw conversation transcript
- Every command run
- Low-value tool logs
- Secrets, tokens, credentials, `.env` content
- Raw data exports or PII
- Speculative notes without evidence (mark `unverified` if kept at all)
- Facts cheaper to re-read from source code than to remember
- Redundant repetitions of things already in `MEMORY.md`

---

## Recall Protocol

Before major work begins:

1. Identify the subsystem or repo area in scope
2. Search session store and `MEMORY.md` by topic / file / component / tag
3. Rank by: relevance first, freshness second, confidence third, active status
4. Read compact summaries first — expand only top matches
5. Inject minimum memory needed — stay within budget

**Token budget (hard defaults):**

| Limit                       | Value            |
|-----------------------------|------------------|
| Candidates to scan          | ≤ 12             |
| Notes to expand             | ≤ 5              |
| Target recall               | 200–800 tokens   |
| Hard ceiling (no override)  | 1200 tokens      |

Do not dump `MEMORY.md` wholesale into context.
Do not inject archive unless explicitly asked.

---

## Source-of-Truth Hierarchy

When memory contradicts current state, resolve in this order:

1. Current user instruction
2. Current repo / file / code state
3. Validated tests / runtime evidence
4. Current operational docs (`MEMORY.md`, `CLAUDE.md`, `INFRA.md`)
5. Durable memory notes
6. Session notes
7. Inference

**Old memory does not override current code truth.**
When stale memory is detected, mark it `superseded` — do not silently merge.

---

## Non-Negotiables

- Never replay full conversation as memory.
- Never load archive by default.
- Compress before storing.
- Filter before recalling.
- Prefer re-reading source over loading memory when source is cheaper.
- Mark speculative notes `unverified` — never silently promote them.
- Secrets never enter memory. Ever.
