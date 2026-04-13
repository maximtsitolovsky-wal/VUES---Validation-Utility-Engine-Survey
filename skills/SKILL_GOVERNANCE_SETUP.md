# SKILL: Governance Setup
**Last Used:** 2026-04-13
**Times Used:** 1

## Trigger
User asks for: "set up Code Puppy", "add memory", "new project governance",
"make sure puppy remembers things", "concrete governance", "memory layer".

## Context — Read First
- Check if `CLAUDE.md` already exists → if yes, read it first.
- Check if `MEMORY.md` already exists → if yes, read it and skip re-creating.
- Read `development.md` and `README.md` to pre-populate memory with settled decisions.
- Read any `prompts/` or architecture docs to extract already-known patterns.

## Steps

1. **Create `CLAUDE.md`** in project root.
   - Must include: MANDATORY MEMORY PROTOCOL (read first, write last).
   - Must include: Project identity (never re-derive).
   - Must include: Standing code rules.
   - Must reference `MEMORY.md` and `skills/INDEX.md`.

2. **Create `MEMORY.md`** in project root.
   - Pre-populate with settled decisions extracted from existing docs.
   - Sections: Architecture, Module Map, Known Risks, Conventions, Session Log.
   - Every settled decision gets `**Closed:** Yes` so Code Puppy doesn't re-open it.

3. **Create `skills/` directory.**

4. **Create `skills/INDEX.md`** with the skill registry table.

5. **Seed at least 2–3 starter skill files** based on tasks already done.

6. **Update `CLAUDE.md`** with SKILL PROTOCOL section.

7. **Update `MEMORY.md`** with today's governance decision in the Session Log.

8. `git add CLAUDE.md MEMORY.md skills/` → `git commit -m "governance: add Code Puppy governance + skill framework"`

## Template

### CLAUDE.md Skeleton
```markdown
# CLAUDE.md — Code Puppy Governance Constitution
## ⚡ MANDATORY MEMORY PROTOCOL
### Step 1 — READ MEMORY.md FIRST
### Step 2 — CHECK skills/INDEX.md
### Step 3 — DO THE WORK
### Step 4 — UPDATE MEMORY.md
### Step 5 — EXTRACT SKILL (if repeatable)
## 📐 Project Identity
## 📏 Standing Code Rules
## 🎓 Skill Protocol
## 🔒 Memory Is Non-Negotiable
```

### MEMORY.md Skeleton
```markdown
# MEMORY.md — <Project> Settled Decisions
## 🏗️ Settled Architecture (Closed)
## ⚠️ Known Risks
## 📏 Conventions
## 📝 Session Log
```

## Notes / Gotchas
- Don't re-create MEMORY.md if it exists. Read it and append.
- Pre-populating from existing docs saves enormous re-thinking time.
- CLAUDE.md is auto-loaded by Code Puppy — it's the enforcement mechanism.
- Skills dir must be committed to git so it persists across sessions.
