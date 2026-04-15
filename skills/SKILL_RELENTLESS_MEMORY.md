# SKILL: Relentless Memory Agent — Session Memory Protocol
**Last Used:** 2026-04-15
**Times Used:** 2

## Trigger
- "take notes this session", "run memory agent", "start memory tracking"
- "save what we learned", "write a handoff", "end of session memory"
- Any session that touches ≥3 files or makes ≥2 decisions
- Starting a new session after complex prior work

## Context — Read First

Before the session:
1. Read `MEMORY.md` QUICK REF (CLAUDE.md Step 1 — mandatory)
2. Read `skills/INDEX.md` (CLAUDE.md Step 2)
3. Check `docs/memory-agent/store/handoff_index.md` — scan last 3 entries
4. If continuing prior work → load most recent full handoff from `docs/memory-agent/store/handoffs/`
5. Run retrieval query with task-relevant tags (see AGENT.md for budget rules)

Files governing this system:
- `docs/memory-agent/AGENT.md` — behavior rules
- `docs/memory-agent/MEMORY_POLICY.md` — what to capture/promote/compress
- `docs/memory-agent/MEMORY_SCHEMA.md` — exact record formats
- `docs/memory-agent/HANDOFF_SPEC.md` — handoff format + emission sequence
- `docs/memory-agent/MEMORY_BACKEND_SPEC.md` — file backend + Python utilities

## Steps

### During the Session
1. Keep an active working scratchpad (in-context only — never write to disk):
   ```
   Objective / Assumptions / Current blocker / Next action
   ```
2. After each meaningful event (decision, fix, failure, open loop), write a session note to `docs/memory-agent/store/session_YYYYMMDD.md` using the format in MEMORY_SCHEMA.md §2.
3. Set `Promote: yes | no | maybe` on each note as you write it.
4. At milestones, compress the session file in place — collapse repeated events.

### At Session End
1. Run the End-of-Task Emission Sequence (HANDOFF_SPEC.md §"End-of-Task"):
   - Compress session notes
   - Evaluate each against promotion gate (MEMORY_POLICY.md §2)
   - Promote passing notes → MEMORY.md + durable.jsonl
   - Mark superseded records
   - Promote open loops as `volatile open_loop` records
2. Write handoff block → `docs/memory-agent/store/handoffs/handoff_YYYYMMDD_HHMM.md`
3. Append one-liner → `docs/memory-agent/store/handoff_index.md`
4. Git commit: `chore: memory emission — <session objective>`

## Template / Example

### Session Note (during work)
```markdown
### Session Note
- Timestamp:  2026-04-14 09:30
- Type:       bugfix
- Scope:      siteowlqa.poll_airtable
- Title:      KeyError on empty attachment list
- Summary:    `process_record()` crashed with KeyError when no attachments present.
              Fixed with `.get("Attachments", [])`. Smoke test passed.
- Evidence:   tests/test_poll_airtable.py::test_empty_attachments — PASSED
- Promote:    yes
```

### Durable JSONL Record
```json
{
  "id": "MEM-20260414-001",
  "date": "2026-04-14",
  "type": "bugfix",
  "status": "active",
  "freshness": "semi-stable",
  "confidence": "high",
  "scope": "siteowlqa.poll_airtable",
  "tags": ["poll-loop", "airtable"],
  "source": "tests/test_poll_airtable.py::test_empty_attachments",
  "summary": "process_record() crashed on empty Attachments field. Fixed with .get('Attachments', []). Verified by test.",
  "why_it_matters": "Prevents silent poll loop crash on any record with no file uploads.",
  "supersedes": null,
  "review_after": "if poll_airtable.py changes"
}
```

### Handoff Index Line
```
| 2026-04-14 09:45 | complete | Fix empty attachment crash in poll loop | Run full E2E test suite against Scout submissions |
```

## Notes / Gotchas

- **Never store credentials or `.env` content in any memory file.** Airtable tokens live in `~/.siteowlqa/config.json` only.
- **Secrets found in session context → do not write to disk. Ever.**
- Archive is append-only — same rule as `archive.py`.
- `MEMORY.md` wins over `durable.jsonl` on conflicts. Always.
- Retrieval budget is hard: ≤5 expanded records, ≤800 tokens. Do not exceed without explicit user instruction.
- Session notes are gitignored by default (they're in `docs/memory-agent/store/`). Make sure `store/` is NOT in `.gitignore` — the store should be committed.
- `durable.jsonl` supersede = rewrite-in-place (small file). Do not use `git mv`. Use the supersede function in MEMORY_BACKEND_SPEC.md.
- If `handoff_index.md` doesn't exist yet, create it with header row before first append.
