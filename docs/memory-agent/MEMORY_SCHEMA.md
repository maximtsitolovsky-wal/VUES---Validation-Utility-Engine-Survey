# MEMORY_SCHEMA.md — SiteOwlQA Memory Agent Schema
> Defines the exact structure of every memory artifact produced by this agent.

---

## Overview

Three active record types. One archive format.

| Type             | Storage Target              | Lifespan        |
|------------------|-----------------------------|-----------------|
| Working Scratchpad | In-context only (never written) | Current task only |
| Session Note     | `docs/memory-agent/store/session_YYYYMMDD.md` | Session → compressed at end |
| Durable Memory   | `MEMORY.md` + `docs/memory-agent/store/durable.jsonl` | Cross-session |
| Archive          | `docs/memory-agent/store/archive/` | Permanent, not injected |

---

## 1. Working Scratchpad

**Never written to disk.** Lives in the agent's active reasoning only.
Use to track current-task state. Overwrite freely.

```
SCRATCHPAD (in-context only)
- Objective:     <one sentence — what am I doing right now>
- Assumptions:   <what I'm treating as true that I haven't verified>
- Current blocker: <what is stopping me, or "none">
- Next action:   <the single next concrete step>
```

Discard at task completion. Never promote scratchpad content directly to durable.
Extract the meaningful outcome (decision, fix, open loop) and promote that instead.

---

## 2. Session Note

Written incrementally during work.
Stored in `docs/memory-agent/store/session_YYYYMMDD.md`.
Compressed and evaluated for promotion at session end.

### Format

```markdown
### Session Note
- Timestamp:  YYYY-MM-DD HH:MM
- Type:       decision | constraint | bugfix | workflow | open_loop | preference | fact
- Scope:      <module, file, subsystem, or "project-wide">
- Title:      <5–10 words — scannable>
- Summary:    <1–3 sentences — operational, compressed>
- Evidence:   <test name, git hash, log line, or "none">
- Promote:    yes | no | maybe
```

### Field Rules

| Field      | Rule                                                              |
|------------|-------------------------------------------------------------------|
| Timestamp  | ISO 8601, local time                                              |
| Type       | Pick the single best fit — do not multi-tag                       |
| Scope      | Use canonical module names (`siteowlqa.config`, not "config file")|
| Title      | Must be scannable in 2 seconds — no vague titles                  |
| Summary    | Compress the outcome + rationale. Drop the journey.               |
| Evidence   | If a fix was verified, name what verified it.                     |
| Promote    | `yes` = promote at session end. `no` = discard. `maybe` = review. |

### Example

```markdown
### Session Note
- Timestamp:  2026-04-14 09:15
- Type:       bugfix
- Scope:      siteowlqa.poll_airtable
- Title:      Silent crash on empty attachment list fixed
- Summary:    `process_record()` raised KeyError when Airtable record had no
              attachments. Fixed by guarding with `.get("Attachments", [])`.
              Smoke test with 0-attachment record passed.
- Evidence:   `tests/test_poll_airtable.py::test_empty_attachments` — PASSED
- Promote:    yes
```

---

## 3. Durable Memory

Two targets — use both for full coverage:

**A. `MEMORY.md` Session Log** — for architectural decisions and major fixes.
Append to the `## 📝 Session Log` section. Also update QUICK REF if relevant.

**B. `docs/memory-agent/store/durable.jsonl`** — for structured recall.
One JSON object per line. Indexed by tags, scope, and ID.

### MEMORY.md Entry Format

```markdown
### YYYY-MM-DD — <short title>
- **Decision:** What happened and why.
- **Impact:** Which files/modules/behaviors changed.
- **Closed:** Yes
```

### JSONL Durable Record Format

```json
{
  "id": "MEM-YYYYMMDD-NNN",
  "date": "YYYY-MM-DD",
  "type": "decision | bugfix | constraint | workflow | open_loop | preference | fact",
  "status": "active | superseded | unverified | archived",
  "freshness": "volatile | semi-stable | stable",
  "confidence": "low | medium | high",
  "scope": "siteowlqa.<module> | project-wide | ops | ui | tests",
  "tags": ["tag1", "tag2"],
  "source": "MEMORY.md | git:<hash> | tests/<file> | docs/<file>",
  "summary": "1–3 sentence compressed fact.",
  "why_it_matters": "What future work this prevents re-doing.",
  "supersedes": "MEM-ID or null",
  "review_after": "YYYY-MM-DD or event (e.g., 'if config.py changes')"
}
```

### Field Rules for JSONL

| Field           | Rule                                                                       |
|-----------------|----------------------------------------------------------------------------|
| `id`            | `MEM-YYYYMMDD-NNN` — NNN = daily sequence number (001, 002…)               |
| `status`        | Default `active`. Mark `superseded` when a newer note replaces this one.   |
| `freshness`     | Assign conservatively — prefer `volatile` when uncertain                   |
| `confidence`    | `high` only when verified by test or runtime. `low` = inferred only.       |
| `scope`         | Use `siteowlqa.<module>` for code; `ops`, `ui`, `tests` for other areas    |
| `tags`          | 2–5 tags, lowercase, hyphenated. From known tag vocabulary (see below).    |
| `source`        | Always link to evidence. Never leave null.                                 |
| `why_it_matters`| Must explain *future value*, not re-describe the event.                    |
| `supersedes`    | ID of old entry this replaces. `null` if new.                              |
| `review_after`  | Date or event that should trigger revalidation.                            |

### Known Tag Vocabulary

```
task-scheduler   config          airtable         archive
poll-loop        sql-server      import-path       dashboard
credentials      models          grading           correction
risk-002         risk-003        memory-system     skill
git              ui              tests             open-loop
windows          entry-point     email             metrics
```

Add new tags sparingly. Prefer existing tags. New tags must be documented here.

---

## 4. Archive Record

Stored in `docs/memory-agent/store/archive/YYYY/`.
Format: same as durable JSONL, but with `"status": "archived"`.

Rules:
- Archive is **never deleted**.
- Archive is **never injected by default**.
- Search archive only when explicitly asked or when diagnosing a regression.
- Move a durable record to archive by: setting `status: archived`, moving JSON line
  to the archive file for the current year.

---

## 5. Handoff Block

See `HANDOFF_SPEC.md` for the full spec.
The handoff block is a structured Markdown block emitted at session end.

Quick reference format:

```markdown
## SiteOwlQA Handoff — YYYY-MM-DD
- Objective:              <what this session was for>
- Status:                 complete | partial | blocked
- Current subsystem:      <module or area last touched>
- Files touched:          <list>
- Decisions made:         <list of titles, linked to MEMORY.md entries>
- Verified fixes:         <list — with evidence>
- Constraints confirmed:  <list>
- Open loops:             <list — with MEM IDs if promoted>
- Next recommended action:<single most important next step>
- Suggested retrieval tags:<tags to pre-load for next session>
```
