# CLAUDE.md — Code Puppy Governance Constitution
# SiteOwlQA_App

> Auto-loaded every session. This is law. Not a suggestion.

---

## ⚡ SESSION PROTOCOL — 5 Steps, Every Time, No Exceptions

```
READ → CHECK SKILLS → EXECUTE → REMEMBER → EXTRACT
```

### 1 · READ `MEMORY.md`
Before touching anything — read `MEMORY.md`.
Extract settled decisions. Do not re-derive closed questions. **Memory beats thinking.**

### 2 · CHECK `skills/INDEX.md`
Scan the Trigger column.
Skill matches your task → open that skill file and follow it. Full stop.
No match → proceed, but you're probably about to write a new skill (see Step 5).

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
| **Stack** | Python · SQL Server · Airtable API · SMTP |
| **Platform** | Windows · single-process · no Docker · no cloud deps |
| **Roadmap** | `development.md` |
| **Settled decisions** | `MEMORY.md` |
| **Architecture** | `prompts/architect_prompt.md` |
| **Skill library** | `skills/INDEX.md` |

---

## 📏 Standing Code Rules

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
| `MEMORY.md` missing | Create it, then proceed |
| `MEMORY.md` exists | Read it before anything else |
| `skills/INDEX.md` missing | Create it, then proceed |
| Skill matches the task | Use it — don't re-derive |
| Decision made this session | Write it to `MEMORY.md` before signing off |
| Task will repeat | Write a skill file before signing off |

**Less thinking. More decisions. Memory + Skills = autonomy.**
