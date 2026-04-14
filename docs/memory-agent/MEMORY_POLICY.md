# MEMORY_POLICY.md — SiteOwlQA Memory Agent Policy
> Governs what gets captured, what gets stored, what gets promoted, and what gets dropped.

---

## The Core Rule

**Capture broadly. Store selectively. Compress aggressively. Retrieve minimally.**

Every other rule in this file is a concrete implementation of that principle.

---

## 1. Capture Rules

Capture a session note when the event is:

| Capture Trigger                                        | Type             |
|--------------------------------------------------------|------------------|
| User states a goal, constraint, or non-goal            | `preference`     |
| A decision is made with rationale                      | `decision`       |
| A file or module is modified and the reason matters    | `decision`       |
| A failure occurs with a root cause identified          | `bugfix`         |
| A fix is verified (test, runtime evidence, etc.)       | `bugfix`         |
| A pattern or workflow is established                   | `workflow`       |
| An assumption is proven wrong                          | `constraint`     |
| A loop is left open at session end                     | `open_loop`      |
| Architecture or module boundary changes                | `decision`       |
| A stable project fact is confirmed or updated          | `fact`           |

Do NOT capture:
- Routine command output with no decision attached
- Repeated confirmations of already-known facts
- Tool logs unless they contain failure evidence
- Anything from `.env`, `config.json`, or credential surfaces
- Raw data or PII

---

## 2. Promotion Rules

A session note **may** be promoted to durable memory only if it passes this gate:

### Promote if:
- It matters beyond this session
- It prevents repeated mistakes
- It records a decision + rationale that took real effort to reach
- It captures a stable user preference or recurring constraint
- It affects architecture, module ownership, or workflow
- It explains a verified fix with evidence
- It is a durable open loop (not resolved this session)

### Reject promotion if:
- The note is noisy or redundant with existing `MEMORY.md` content
- The note is stale (superseded within the same session)
- The information is cheap to rediscover by reading source
- The note is speculative and unverified (keep as `unverified` in session store only)
- The fact is already in `MEMORY.md` QUICK REF

### Promotion destination:
- High-value decisions → append to `MEMORY.md` Session Log
- Reusable structured facts → write to `docs/memory-agent/store/durable.jsonl`
- Both surfaces are valid; prefer `MEMORY.md` for architectural decisions

---

## 3. Compression Rules

Memory stores meaning, not transcript.

**Before writing any note:**

| Rule                                              | Example                                                   |
|---------------------------------------------------|-----------------------------------------------------------|
| Collapse repeated events into one note            | 3 failed import attempts → one root cause note            |
| Preserve rationale and outcome — drop the journey | Not "we tried X then Y then Z" → "Z fixed it because..."  |
| Use canonical module/file names                   | `siteowlqa.config`, not "the config file"                 |
| Split unrelated facts into separate notes         | Don't bundle a bugfix with an architecture decision        |
| Summaries must be dense and operational           | No filler, no hedging, no narrative throat-clearing        |
| Store only what costs more to re-derive than keep | If `grep` finds it in 2 seconds, don't memorize it        |

**Target note sizes:**

| Format    | Size                  | When to use                                      |
|-----------|-----------------------|--------------------------------------------------|
| micro     | 1 line                | Simple stable fact, preference, or constraint    |
| standard  | 1–3 sentences         | Most decisions, bugfixes, workflow notes         |
| extended  | 4–8 sentences         | Only when evidence or steps matter for recall    |
| handoff   | Structured block      | End of session / task — see `HANDOFF_SPEC.md`   |

---

## 4. Freshness Rules

Every durable memory entry has a **freshness class**:

| Class        | Meaning                                                     |
|--------------|-------------------------------------------------------------|
| `stable`     | Unlikely to change. Architecture decisions, closed rules.   |
| `semi-stable`| May change with new features or environment shifts.         |
| `volatile`   | Expected to change. Open loops, in-progress work.           |

Revalidate a memory entry when:
- A relevant file changes (check `git log` for touched modules)
- A test contradicts the stored note
- User instruction explicitly overrides it
- Runtime behavior changes (e.g., Task Scheduler config, port changes)
- A newer verified fix replaces an older one

**SiteOwlQA-specific freshness signals:**
- `main.py` touched → revalidate poll loop notes
- `config.py` touched → revalidate credential/env notes
- `ops/windows/` touched → revalidate Task Scheduler notes
- `archive.py` touched → revalidate append-only constraint notes
- Airtable base IDs referenced → confirm against `~/.siteowlqa/config.json`

---

## 5. Conflict Rules

When a memory note conflicts with current code state or user instruction:

1. Do **not** silently merge.
2. Check which source is newer (git log, file mtime, user statement).
3. Apply the source-of-truth hierarchy (see `AGENT.md`).
4. Mark the older note `superseded` with a reason.
5. Write a new note that reflects the current truth.
6. Never delete archive entries — supersede and move on.

**Conflict is always explicit. Silent merging is a bug.**

---

## 6. Token Discipline Rules

These are hard rules. Not suggestions.

| Rule                                                             |
|------------------------------------------------------------------|
| Never replay full conversation history as memory                 |
| Never dump all of `MEMORY.md` into context — filter first        |
| Never inject raw logs by default                                 |
| Never load archive unless the user explicitly asks               |
| Compress before storing — never store first, compress later      |
| Filter before recalling — never inject, then filter              |
| Prefer re-reading source code over loading memory when cheaper   |
| Stay within the retrieval token budget (see `AGENT.md`)          |

**Memory's job is to shorten future work. If loading memory costs more tokens
than it saves, it has failed its purpose.**

---

## 7. SiteOwlQA-Specific Policy Additions

These rules apply because of known project patterns:

| Pattern                                     | Policy                                                          |
|---------------------------------------------|-----------------------------------------------------------------|
| `os.getenv` found outside `config.py`       | Capture as `bugfix` — it's always a violation                   |
| Archive delete attempted                    | Capture as `constraint` — archive is append-only, always        |
| Task Scheduler launch path changes          | Promote to durable — affects restart reliability                |
| Airtable base ID or token changes           | Do NOT store in memory — store in `~/.siteowlqa/config.json`    |
| RISK-002 / RISK-003 progress                | Always promote open loops to durable as `volatile`              |
| `memory.py` lesson retrieval logic changes  | Promote to durable — affects the memory system itself           |
| Dashboard template vs served output         | Stable fact: edit `ui/executive_dashboard.html`, not `output/`  |
| File exceeds 600 lines                      | Capture as `constraint` + trigger skill check                   |
