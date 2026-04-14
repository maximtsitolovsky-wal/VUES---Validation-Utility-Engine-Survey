# skills/INDEX.md — Code Puppy Skill Library
# SiteOwlQA_App

> Code Puppy reads this BEFORE tackling any task.
> If a skill matches the task pattern → use it. Do not re-derive.
> After completing a task that will repeat → extract a new skill here.

---

## How to Use This Index

1. Read the trigger column.
2. If your task matches → open the skill file and follow it.
3. Don't improvise what is already codified.
4. After a new repeatable task → add a row here and create the skill file.

---

## Skill Registry

| Skill File | Triggers (when to use it) | Tags |
|---|---|---|
| [SKILL_SKILL_EXTRACTION.md](SKILL_SKILL_EXTRACTION.md) | Runs automatically at end of every task (CLAUDE.md Step 5). "extract a skill", "save this as a pattern", "we'll do this again" | meta, skills, autonomy |
| [SKILL_GOVERNANCE_SETUP.md](SKILL_GOVERNANCE_SETUP.md) | "set up Code Puppy", "new project", "add memory", "add governance" | governance, bootstrap, memory |
| [SKILL_FLAT_HTML_REPORT.md](SKILL_FLAT_HTML_REPORT.md) | "build a report", "flat HTML", "dashboard", "chart", "visualise data" | reporting, html, chart.js, tailwind |
| [SKILL_GIT_FOCUSED_COMMIT.md](SKILL_GIT_FOCUSED_COMMIT.md) | "commit this", "git commit", "push changes", "save changes" | git, hygiene, version-control |
| [SKILL_GIT_TRUTH_GUARD.md](SKILL_GIT_TRUTH_GUARD.md) | "make sure it got pushed", "verify git", "show me receipts", "don't let the agent lie" | git, verification, orchestration, governance |
| [SKILL_ORCHESTRATION_MAP.md](SKILL_ORCHESTRATION_MAP.md) | "show me the flow", "visualise pipeline", "orchestration diagram", "how does it work" | visualisation, html, pipeline |
| [SKILL_RELENTLESS_MEMORY.md](SKILL_RELENTLESS_MEMORY.md) | "take notes this session", "run memory agent", "write a handoff", "end of session", any session with ≥3 files or ≥2 decisions | memory, handoff, session, governance |

---

## Skill File Format

Every skill file must follow this structure:

```markdown
# SKILL: <Name>
**Last Used:** YYYY-MM-DD
**Times Used:** N

## Trigger
When to apply this skill (user phrases / task patterns).

## Context — Read First
What files or state to read before executing.

## Steps
Numbered, concrete, executable steps. No fluff.

## Template / Example
Paste-ready template or concrete example output.

## Notes / Gotchas
Edge cases, things that have gone wrong, warnings.
```

---

## Skill Extraction Rule

After any Code Puppy task: ask "will I do this again?"
- YES → create a skill file, add a row above, commit.
- NO  → skip.

One task = one skill. Keep skills focused. DRY applies to skills too.
