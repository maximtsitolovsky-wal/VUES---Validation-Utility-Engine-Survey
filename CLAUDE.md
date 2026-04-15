# CLAUDE.md — Code Puppy Governance Constitution
# SiteOwlQA_App

> Auto-loaded every session. This is law. Not a suggestion.
> Violation = re-deriving settled work = wasting Maxim's time. Don't.

---

## ⚡ SESSION PROTOCOL — 5 Steps, Every Time, No Exceptions

```
READ → PROVE → CHECK SKILLS → EXECUTE → REMEMBER → EXTRACT
```

### 1 · READ `MEMORY.md` — THEN PROVE YOU READ IT

Before touching **anything** — open `MEMORY.md` and scan the QUICK REF block.

> **If this is a continuation:** Load `docs/memory-agent/store/handoff_index.md` FIRST.
> Pick up the last entry. Load that full handoff if the objective is complex or multi-file.
> Then read MEMORY.md. Then state the MEMORY CHECK. In that order.

**You must explicitly state (out loud, in your response) before any action:**

> 🧠 MEMORY CHECK
> - Stack: [one line summary]
> - Config owner: config.py / `~/.siteowlqa/config.json`
> - Open risks relevant to this task: [RISK-002 / RISK-003 / none]
> - Last decision that affects this task: [date — title / none]
> - Closed questions I will NOT re-open: [list or none]

If you cannot fill this in — you haven't read MEMORY.md. Stop. Read it. Fill it in. Then act.

**Memory beats thinking. Every time.**

### 2 · CHECK `skills/INDEX.md`
Scan the Trigger column.
Skill matches your task → open that skill file and follow it. Full stop.
No match → proceed, but you're probably about to write a new skill (see Step 6).

### 3 · EXECUTE
Use settled context. Skip the preamble. Act.

### 4 · WRITE to `MEMORY.md`
Any decision, architectural change, new pattern, or bug root cause → append to `MEMORY.md`:

```markdown
### YYYY-MM-DD — <short title>
- **Decision:** What and why.
- **Impact:** Which files/modules.
- **Closed:** Yes
```

Also update the **Last 3 Decisions** list in the QUICK REF block (pop the oldest, push the new one).

Nothing worth writing? Still say: *"Memory unchanged — no new decisions."*

### 5 · EXTRACT a skill (if it will repeat)
Ask: *"Will I do this again?"*
- **Yes** → create `skills/SKILL_<NAME>.md`, add a row to `skills/INDEX.md`, commit.
- **No** → skip. YAGNI applies to skills too.

Skill format (non-negotiable):
```markdown
# SKILL: <Name>
**Last Used:** YYYY-MM-DD  **Times Used:** N

## Trigger
## Context — Read First
## Steps
## Template / Example
## Notes / Gotchas
```

Used a skill and found a better way? Update the file. Bump `Times Used`. Commit `docs: update SKILL_<NAME>`.

---

## 📐 Project Identity (Never Re-Derive)

| | |
|---|---|
| **App** | SiteOwlQA — automated vendor QA pipeline |
| **Stack** | Python · SQL Server · Airtable API (email via Airtable automations — no SMTP) |
| **Platform** | Windows · single-process · Docker available (dev only, port 8765) · no cloud deps |
| **Roadmap** | `development.md` |
| **Settled decisions** | `MEMORY.md` |
| **Architecture** | `prompts/architect_prompt.md` |
| **Skill library** | `skills/INDEX.md` |

---

## 📐 Standing Code Rules

- DRY · YAGNI · SOLID · Zen of Python — always.
- Files ≤ 600 lines. Split on cohesion, not line count.
- `config.py` is the only module that calls `os.getenv`. No exceptions.
- SQL lives in `sql.py`. Types live in `models.py`. Not scattered.
- Archive is **append-only**. Never delete lessons or execution records.
- Main poll loop **never crashes**. Catch at the record level.
- Commit after every completed change. Small, scoped, clear message.
- Never force-push to git.

---

## 🔒 Non-Negotiables

| Condition | Action |
|---|---|
| Session starts | State the MEMORY CHECK block before any file operation |
| `MEMORY.md` missing | Create it from scratch, then state MEMORY CHECK |
| `MEMORY.md` exists | Read QUICK REF, state MEMORY CHECK, then proceed |
| `skills/INDEX.md` missing | Create it, then proceed |
| Skill matches the task | Use it — don't re-derive |
| Decision made this session | Append to `MEMORY.md` + update Last 3 Decisions |
| Task will repeat | Write a skill file before signing off |
| `os.getenv` outside config.py | Reject and fix — not negotiate |

**Less thinking. More decisions. Memory + Skills = autonomy.**
