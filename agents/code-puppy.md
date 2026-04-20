# Agent: code-puppy
**Category:** Dev Agent  
**Type:** Code Puppy Sub-Agent  
**ID:** `code-puppy-12b591`

---

## What It Is
The main Code Puppy coding assistant. General-purpose — writes, reads, edits, runs
shell commands, runs tests, commits to git. The agent you're talking to right now.

## Role in This Project
- Primary development assistant for VUES
- Implements features, fixes bugs, runs the test suite
- Applies skills from `skills/INDEX.md`
- Reads `MEMORY.md` and `CLAUDE.md` at session start
- Delegates to other sub-agents when specialised tasks arise
- Enforces project rules: DRY, YAGNI, ≤600 line files, no `os.getenv` outside config.py

## How to Invoke
You're already using it. It's the default Code Puppy agent.

## Governance Files It Reads
| File | Purpose |
|---|---|
| `CLAUDE.md` | Session protocol — 5 steps, every session |
| `MEMORY.md` | Settled decisions, open risks, quick ref |
| `skills/INDEX.md` | Skill library — check before re-deriving anything |
| `development.md` | Active roadmap and delivery tracking |

## Key Rules It Enforces (from CLAUDE.md)
- State a MEMORY CHECK block before any file operation
- `config.py` is the only caller of `os.getenv` — anywhere else = reject and fix
- Archive is append-only — never delete lessons or execution records
- Commit after every completed change
- Never force-push

## Handoff to Other Agents
| Task | Delegates To |
|---|---|
| Airtable API operations | `airtable` agent |
| Publishing HTML reports | `share-puppy` agent |
| Cross-project governance | `chiefmaxim` agent |
| Project-scoped dev work | `siteowlqa-dev` agent |
