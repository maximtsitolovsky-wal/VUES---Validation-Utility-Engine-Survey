# SiteOwlQA — Agent Registry

Complete catalogue of every agent, session role, and prompt-defined persona
used in this project. Three categories, clearly separated.

---

## Category 1 — Code Puppy Sub-Agents (dev-time)
Invoked during dev sessions via `/agent <name>`. No footprint in the app's source code.

| Agent | File | What It Does |
|---|---|---|
| `code-puppy` | `code-puppy.md` | Main dev assistant — reads, writes, runs, commits |
| `siteowlqa-dev` | `siteowlqa-dev.md` | Project-scoped dev agent, enforces module ownership + git discipline |
| `chiefmaxim` | `chiefmaxim.md` | Cross-project governance, meta-level decisions above this project |
| `airtable` | `airtable.md` | Airtable API operations — inspect base, patch records, debug field mapping |
| `share-puppy` | `share-puppy.md` | Publishes HTML reports + dashboards to puppy.walmart.com/sharing |
| `integrity-marshal` | `Integrity_Marshal.md` | Audits agents for truthfulness, memory compliance, stale-state, evidence-backed completion |
| `relayops-coordinator` | `relayops-coordinator.md` | Multi-agent coordination — message passing, task claiming, conflict detection, handoffs |

---

## Category 2 — Session Role Personas (dev-time)
Code Puppy adopts these roles during dev sessions to enforce specific reasoning patterns.
Each maps to a prompt file in `prompts/` and/or a deterministic runtime module.

| Role | File | Prompt Source | Runtime Module | LLM? |
|---|---|---|---|---|
| Architect | `architect.md` | `prompts/architect_prompt.md` | _(none — session reasoning only)_ | ❌ |
| Generator | `generator.md` | `prompts/generator_prompt.md` | _(none — session reasoning only)_ | ❌ |
| Reviewer | `reviewer.md` | `prompts/reviewer_prompt.md` | `src/siteowlqa/reviewer.py` | ❌ |
| Grading Authority | `grading-authority.md` | `prompts/grading_prompt.md` | `src/siteowlqa/python_grader.py` | ❌ |
| Git Truth Guard | `git-truth-guard.md` | `prompts/git_truth_guard_prompt.md` | `tools/git_truth_guard.py` | ❌ |

> **Note:** `reviewer.py` and `python_grader.py` are fully deterministic — no LLM calls.
> The session role and the runtime module implement the same rule set.

---

## Category 3 — Runtime LLM Agents (app code + tools)
pydantic-ai `Agent` instances that call the Element LLM Gateway at runtime.

| Agent | File | Location | When It Runs | LLM? |
|---|---|---|---|---|
| Element LLM Gateway | `element-llm-gateway.md` | `src/siteowlqa/weekly_highlights.py` | Weekly executive report generation | ✅ |
| Docker Platform Engineer | `docker-platform-engineer.md` | `tools/docker_platform_engineer.py` | On-demand: `python tools/docker_platform_engineer.py` | ✅ |
| System Bottleneck Auditor | `system-bottleneck-auditor.md` | `tools/system_bottleneck_auditor.py` | On-demand: `python tools/system_bottleneck_auditor.py` | ✅ |
| Specialist Output Validator | `specialist-output-validator.md` | `tools/specialist_output_validator.py` | On-demand: validates outputs of the above tool agents | ✅ |

### ⚠️ Planned — Not Yet Built
| Agent | Referenced In | Status |
|---|---|---|
| Memory & Token Optimization Engineer | `tools/specialist_output_validator.py` | ❌ Not implemented — no source file, no output yet |

---

## Orchestration Contract
When multiple session roles are active in one task, they must operate in this order:

```
1. Architect    → defines scope, constraints, module boundaries
2. Generator    → implements the change
3. Reviewer     → checks code quality and business rules
4. Git Truth Guard → verifies commit + push receipts
                    ← task is only COMPLETE after this step
```

---

## LLM Gateway — Shared Configuration
All three runtime LLM agents read from `AppConfig` (via `config.py`):

| Config Key | Purpose |
|---|---|
| `element_llm_gateway_url` | Direct URL override (takes priority) |
| `element_llm_gateway_project_id` | Auto-builds URL if no direct URL |
| `element_llm_gateway_api_key` | API key sent as `X-Api-Key` header |
| `element_llm_gateway_model` | Model name — default: `element:gpt-4o` |
| `wmt_ca_path` | Walmart CA cert path for TLS |

Gateway URL pattern:
```
https://ml.prod.walmart.com:31999/element/genai/project/{project_id}/openai/v1
```
Reference: https://wmlink.wal-mart.com/genai-access

All three agents degrade gracefully — they have static fallbacks when the
gateway is unavailable or unconfigured.

---

## Key Invariant
> **The grading pipeline has zero LLM calls.**
> PASS / FAIL / ERROR is always 100% deterministic.
> LLM is used only for reporting (weekly highlights) and tooling (infra design, bottleneck audit).

---

## File Count
```
agents/
├── README.md                      ← this file
│
├── [Category 1 — Code Puppy Sub-Agents]
├── code-puppy.md
├── siteowlqa-dev.md
├── chiefmaxim.md
├── airtable.md
├── share-puppy.md
├── Integrity_Marshal.md
├── relayops-coordinator.md
│
├── [Category 2 — Session Role Personas]
├── architect.md
├── generator.md
├── reviewer.md
├── grading-authority.md
├── git-truth-guard.md
│
└── [Category 3 — Runtime LLM Agents]
    ├── element-llm-gateway.md
    ├── docker-platform-engineer.md
    ├── system-bottleneck-auditor.md
    └── specialist-output-validator.md

# Planned (not yet built)
#   memory-token-engineer.md  ← referenced in specialist_output_validator.py
```
