# HANDOFF_SPEC.md — SiteOwlQA Memory Agent Handoff Specification
> Restart-safe. Session-safe. Governs end-of-task memory emission.

---

## Purpose

A handoff block is the agent's final act in a session.
It creates a restart-safe summary that the next agent instance can
consume without replaying the full session.

Its goal: make the next session start in 30 seconds, not 5 minutes.

---

## When to Emit a Handoff

Emit a handoff block when **any** of the following is true:

| Condition                                                     |
|---------------------------------------------------------------|
| Session is ending (explicit or inferred)                      |
| A significant task is complete                                |
| The agent is handing off to a different agent or model        |
| An open loop is being left unresolved                         |
| More than 3 meaningful decisions were made this session       |
| The task touched more than 2 files or modules                 |
| A RISK-002 or RISK-003 status changed                         |

Do **not** emit handoffs for trivial single-step tasks (e.g., "what does X do?")
unless they produced a notable decision.

---

## Handoff Block Format

```markdown
## SiteOwlQA Handoff — YYYY-MM-DD
- Objective:              <one sentence — what was the session for>
- Status:                 complete | partial | blocked
- Current subsystem:      <canonical module or area name>
- Files touched:          
    - `path/to/file.py` — <why touched>
    - `path/to/file2.md` — <why touched>
- Decisions made:         
    - <title> → MEMORY.md YYYY-MM-DD
    - <title> → MEM-ID in durable.jsonl
- Verified fixes:         
    - <fix title> — verified by <test name | runtime evidence | git hash>
- Constraints confirmed:  
    - <constraint that was reinforced this session>
- Open loops:             
    - <loop title> — MEM-ID | RISK-ID | "unpromoted"
- Next recommended action: <single clearest next step — be specific>
- Suggested retrieval tags: <2–5 tags from known vocabulary>
```

---

## Field Rules

| Field                     | Rule                                                                   |
|---------------------------|------------------------------------------------------------------------|
| `Objective`               | One sentence. What the agent was hired to do this session.             |
| `Status`                  | `complete` = all objectives done. `partial` = some done. `blocked` = stopped by external. |
| `Current subsystem`       | Canonical name. Use `siteowlqa.<module>` for code areas.               |
| `Files touched`           | Every file modified or meaningfully read. Include the reason.          |
| `Decisions made`          | Link each to either MEMORY.md date or durable.jsonl MEM-ID.            |
| `Verified fixes`          | Only list fixes with evidence. Unverified fixes go in open loops.      |
| `Constraints confirmed`   | Rules, architecture limits, or non-goals that were explicitly reinforced. |
| `Open loops`              | Anything left unresolved. Promote to durable as `volatile` open_loop.  |
| `Next recommended action` | Specific, actionable, not vague. Bad: "continue work." Good: "Run RISK-002 validation against ProjectID after normalization step." |
| `Suggested retrieval tags`| Tags the next session should pre-load. From known tag vocabulary.      |

---

## Restart-Safety Rules

A handoff block is restart-safe when:

1. The next agent can read it cold and know where to start.
2. It contains no assumptions that require session history to interpret.
3. All file references use full repo-relative paths.
4. All module references use canonical `siteowlqa.<module>` names.
5. Open loops are promoted to `durable.jsonl` before the session closes.
6. The `Next recommended action` is specific enough to act on without context.

**A handoff that requires the next agent to also read the full session log has failed.**

---

## Handoff Storage

Write the handoff block to:

```
docs/memory-agent/store/handoffs/handoff_YYYYMMDD_HHMM.md
```

Also append a compressed one-liner to:

```
docs/memory-agent/store/handoff_index.md
```

### `handoff_index.md` line format:

```
| YYYY-MM-DD HH:MM | <status> | <objective — one sentence> | <next action — one sentence> |
```

This index is the fast-scan surface for the next session before loading a full handoff.

---

## Handoff Consumption Protocol

At session start, if a prior handoff exists:

1. Read `handoff_index.md` — scan last 3 entries (≤ 30 seconds).
2. If the current task is a continuation → load the most recent full handoff.
3. If the current task is unrelated → skip full handoff; load only suggested tags.
4. Pre-load suggested retrieval tags from prior handoff into retrieval query.
5. State what was loaded in the MEMORY CHECK block (CLAUDE.md Step 1).

**Token cost of handoff consumption must be ≤ 400 tokens for index scan.**
**Full handoff load must be ≤ 800 tokens.**

---

## End-of-Task Memory Emission Sequence

Run this sequence at the close of every substantive session, in order:

```
1. Compress session notes — drop noise, preserve decisions and evidence.
2. Evaluate each note against promotion gate (MEMORY_POLICY.md §2).
3. Promote passing notes:
   a. Architectural decisions → MEMORY.md Session Log + update QUICK REF if needed.
   b. Structured facts → durable.jsonl
4. Mark superseded durable records (status: superseded, not deleted).
5. Promote open loops to durable.jsonl as volatile open_loop records.
6. Write handoff block to docs/memory-agent/store/handoffs/handoff_YYYYMMDD_HHMM.md
7. Append one-liner to handoff_index.md
8. Git commit: "chore: memory emission — <session objective>"
```

Never skip step 8. Memory that isn't committed doesn't survive a reset.

---

## Example Handoff

```markdown
## SiteOwlQA Handoff — 2026-04-14
- Objective:              Build and deploy the Relentless Memory Agent docs.
- Status:                 complete
- Current subsystem:      docs/memory-agent
- Files touched:
    - `docs/memory-agent/AGENT.md` — created (core behavior spec)
    - `docs/memory-agent/MEMORY_POLICY.md` — created (capture/promotion/compression rules)
    - `docs/memory-agent/MEMORY_SCHEMA.md` — created (all record formats)
    - `docs/memory-agent/HANDOFF_SPEC.md` — created (this file)
    - `docs/memory-agent/MEMORY_BACKEND_SPEC.md` — created (file backend)
    - `skills/SKILL_RELENTLESS_MEMORY.md` — created (skill playbook)
    - `skills/INDEX.md` — updated (new skill row added)
- Decisions made:
    - Memory agent is a behavioral layer, not a separate process → MEMORY.md 2026-04-14
    - Durable store: MEMORY.md + durable.jsonl dual-target → MEM-20260414-001
- Verified fixes:         none (documentation session)
- Constraints confirmed:
    - Airtable credentials never enter memory — stay in config.json only
    - Archive is append-only — never delete
- Open loops:
    - `memory.py` lesson retrieval upgrade to semantic search (>100 lessons) — see MEMORY.md open upgrade #3
- Next recommended action: Create `docs/memory-agent/store/` directory structure
                           and seed with first durable.jsonl entry from this session.
- Suggested retrieval tags: memory-system, skill, config, open-loop
```
