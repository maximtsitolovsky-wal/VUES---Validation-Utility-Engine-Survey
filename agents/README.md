# agents/ — SiteOwlQA Agent Registry

> Every AI agent touching this project lives here.
> Two categories: **Dev Agents** (Code Puppy sub-agents used by Maxim in dev sessions)
> and **Runtime Agents** (pydantic-ai `Agent` instances running inside the application).

---

## Quick Reference

| Agent | Category | Invoked By | Primary Role |
|---|---|---|---|
| [code-puppy](code-puppy.md) | Dev | Maxim | Main coding assistant (current) |
| [siteowlqa-dev](siteowlqa-dev.md) | Dev | Maxim | Project-scoped dev agent |
| [chiefmaxim](chiefmaxim.md) | Dev | Maxim | Cross-project governance |
| [airtable](airtable.md) | Dev | Maxim | Airtable API operations |
| [share-puppy](share-puppy.md) | Dev | Maxim | Publish HTML reports |
| [element-llm-gateway](element-llm-gateway.md) | Runtime | `weekly_highlights.py` | Weekly executive report generation |

---

## Category Definitions

### Dev Agents
Code Puppy sub-agents invoked interactively during development sessions.
They have no footprint in the app's source code — they operate at the
conversation / tooling layer and modify files, run tests, commit to git, etc.

To invoke: `/agent <name>` in Code Puppy, or let `code-puppy` delegate automatically.

### Runtime Agents
pydantic-ai `Agent` instances instantiated inside the running SiteOwlQA application.
They consume the Element LLM Gateway and run as part of the weekly highlights pipeline.
They are NOT conversational — they run synchronously as a step in a function call.

---

## Skills Index
Skills are behavioral layers loaded by dev agents, not standalone processes.
They live in `skills/` and are referenced here for discoverability.

| Skill | Trigger |
|---|---|
| `SKILL_RELENTLESS_MEMORY` | Session with ≥3 files or ≥2 decisions — take notes |
| `SKILL_GIT_TRUTH_GUARD` | Verify git push with receipts |
| `SKILL_GIT_FOCUSED_COMMIT` | Any git commit operation |
| `SKILL_FLAT_HTML_REPORT` | Build a dashboard or chart report |
| `SKILL_ORCHESTRATION_MAP` | Visualise pipeline / show the flow |
| `SKILL_GOVERNANCE_SETUP` | New project or governance bootstrap |
| `SKILL_SKILL_EXTRACTION` | End of every task — extract repeatable patterns |
| `memory-and-token-optimization-engineer` | Memory/token audit on any LLM app |

Full skill specs: [`skills/INDEX.md`](../skills/INDEX.md)
Memory-token audit report: [`docs/memory_token_optimization_report.md`](../docs/memory_token_optimization_report.md)
