# CLAUDE.md — Code Puppy Governance Constitution
# SiteOwlQA_App

> This file is auto-loaded by Code Puppy at the start of every session.
> It is law. Not a suggestion.

---

## ⚡ MANDATORY MEMORY PROTOCOL

**Every single session, no exceptions, no shortcuts:**

### Step 1 — READ MEMORY.md FIRST
Before writing a single line of code, before asking a clarifying question, before doing anything:

```
READ MEMORY.md
```

Extract the relevant settled decisions. Do not re-derive what is already written there.
Do not re-debate closed questions. **Memory beats thinking.**

### Step 2 — DO THE WORK
Use the settled context from MEMORY.md to act faster and more decisively.
Skip the preamble. Skip re-analyzing what is already known. Just execute.

### Step 3 — UPDATE MEMORY.md LAST
After completing any task that involves a decision, architectural change, new pattern,
bug fix root cause, or convention established — append it to MEMORY.md under the
correct section using this format:

```markdown
### YYYY-MM-DD — <short title>
- **Decision:** What was decided and why.
- **Impact:** Which files/modules are affected.
- **Closed:** Yes (do not re-open unless explicitly asked).
```

**If a task touched nothing worth remembering, you still confirm: "Memory unchanged — no new decisions."**

---

## 📐 Project Identity (Never Re-Derive This)

- **App:** SiteOwlQA — automated vendor QA pipeline
- **Stack:** Python, SQLite/SQL Server, Airtable API, SMTP email
- **Platform:** Windows, single-process, no Docker, no cloud deps
- **Source of truth for roadmap:** `development.md`
- **Source of truth for settled decisions:** `MEMORY.md`
- **Source of truth for architecture:** `prompts/architect_prompt.md`

---

## 📏 Standing Code Rules (Always Enforced)

- DRY, YAGNI, SOLID — always.
- Zen of Python — always.
- Files stay under 600 lines. Split on cohesion, not line count.
- Config lives in `config.py`. No module calls `os.getenv` directly.
- SQL lives in `sql.py`. Not scattered.
- All shared types live in `models.py`.
- Archive is **append-only**. Never delete lessons or execution records.
- The main poll loop **never crashes**. Catch at record level.
- Commit after every completed change. Small, scoped, clear commit messages.
- Never force-push to git.

---

## 🔒 Memory Is Non-Negotiable

If MEMORY.md does not exist → create it before proceeding.
If MEMORY.md exists → read it before proceeding.
If a decision was made today → write it to MEMORY.md before signing off.

**Less thinking. More decisions. Memory is the shortcut.**
