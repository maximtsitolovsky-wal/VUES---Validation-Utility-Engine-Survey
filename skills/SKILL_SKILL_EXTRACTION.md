# SKILL: Skill Extraction
**Last Used:** 2026-04-13  **Times Used:** 1

## Trigger
Runs automatically at the end of EVERY task (per CLAUDE.md Step 5).
Also triggered explicitly by: "extract a skill from this", "save this as a skill",
"we'll do this again", "turn this into a pattern".

---

## The Core Question
> "Will I do this same TYPE of task again — on this project or any other?"

- **Yes, repeatedly** → extract a skill.
- **Yes, but it's too project-specific** → log a decision in `MEMORY.md` instead.
- **No** → skip both. YAGNI.

---

## Skill vs Decision vs One-off

| What it is | Where it goes | Example |
|---|---|---|
| A repeatable **process** (how to DO something) | `skills/SKILL_<NAME>.md` | "build a flat HTML report" |
| A one-time **choice** (what was decided) | `MEMORY.md` session log | "we use calamine engine for xlsx" |
| A one-off task, never repeats | nowhere — drop it | "rename this specific column" |

---

## How to Extract (Step by Step)

**1. Identify the repeatable pattern.**
Look at what you just did. Strip the project-specific details.
Ask: "what is the generic version of this task?"

> Bad: "reload Camera&Alarm Ref Data from two Excel sheets into dbo.ReferenceRaw"
> Good: "bulk-reload a SQL table from a multi-sheet Excel file"

**2. Name it.**
Format: `SKILL_<VERB>_<NOUN>` — action-first, generic.
- `SKILL_BUILD_HTML_REPORT` not `SKILL_REPORT`
- `SKILL_EXTRACT_SKILL` not `SKILL_META`
- `SKILL_REFACTOR_MODULE` not `SKILL_CLEANUP`

**3. Write the Trigger section first.**
This is the most important field. It must match how a human would ASK for this — not how it's implemented.
Write 3–5 natural-language phrases that would cause this skill to activate.

**4. Write Steps — concrete and executable.**
3–7 steps. No fluff. Each step should be something Code Puppy can literally do.
If a step is vague ("review the output"), make it specific ("check that X field is non-null").

**5. Add one Template or Example.**
Paste-ready is ideal. Even a skeleton is better than none.
This is what saves the most time on reuse.

**6. Add Gotchas — only real ones.**
Things that actually went wrong or that are easy to miss.
Don't invent hypothetical warnings. YAGNI applies to gotchas too.

**7. Add a row to `skills/INDEX.md`.**
One row. Trigger column must match your Trigger section.

**8. Commit.**
`docs: add SKILL_<NAME>`

---

## Minimum Viable Skill

A skill is shippable when it has:
- ✅ A trigger (what activates it)
- ✅ 3–7 executable steps
- ✅ One template or concrete example

Everything else is optional. Don't gold-plate it — the skill improves on reuse.

---

## When NOT to Extract

- The task applied an existing skill → just bump `Times Used` on that skill.
- The task was purely project-specific data work (a one-off migration, a specific fix).
- The task was so simple it's faster to just do it than read a skill file.
- You're extracting a skill that already exists under a different name → update the existing one, don't duplicate.

---

## Updating an Existing Skill

If you used a skill and found a better way:
1. Open the skill file.
2. Update the relevant section (usually Steps or Gotchas).
3. Bump `Times Used`. Update `Last Used`.
4. Commit: `docs: update SKILL_<NAME> — <what changed>`

Do not create a new skill file for an improvement to an existing one. DRY.

---

## Notes / Gotchas

- The Trigger is the hardest part to write well. Spend most of your time there.
- Generic > specific in skill files. Project-specific details belong in MEMORY.md.
- Skills compound. A mediocre skill on first extraction becomes excellent by the third use.
- If you can't write the trigger in 30 seconds, the pattern isn't clear enough yet. Log a decision in MEMORY.md and revisit after seeing it repeat.
