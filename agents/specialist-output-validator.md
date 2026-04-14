# Agent: specialist-output-validator
**Category:** Tool Agent  
**Type:** pydantic-ai `Agent` instance (run-on-demand)  
**LLM:** `element:gpt-4o` via Walmart Element LLM Gateway  
**CLI Tool:** `tools/specialist_output_validator.py`  
**LLM Agent:** ✅ Yes — `Agent(model, instructions=_SYSTEM_PROMPT)` called in `_run_llm_validation()`

---

## What It Is
A quality-gate agent that reviews the output of other specialist agents and
applies a strict rubric to determine PASS / FAIL / NOT_RUN for each.
Run on demand after other tool agents have produced their output.

This is the meta-agent — it validates the validators.

## Usage
```bash
python tools/specialist_output_validator.py             # LLM + browser
python tools/specialist_output_validator.py --no-llm   # static structural checks only
python tools/specialist_output_validator.py --no-browser
```

## Specialists It Reviews
| Specialist | Output It Reads | Built? |
|---|---|---|
| System Bottleneck Auditor | `output/bottleneck_audit_*.md` + `.html` | ✅ Yes |
| Docker Platform Engineer | `infra/` artifacts + `output/docker_platform_*.html` | ✅ Yes |
| Memory & Token Optimization Engineer | `output/memory_token_*.md` | ❌ Not yet built |

> **RISK:** The Memory & Token Optimization Engineer is referenced as a planned agent
> but has not been implemented. When built, it needs an `agents/memory-token-engineer.md` doc.

## LLM System Prompt Role
```
You are Specialist Output Validator.
Review the output from specialist agents and apply the rubric below.
Be strict. Do not confuse verbosity with quality. Reject fluff.
```

## Rubric Per Agent
### System Bottleneck Auditor
Must contain: bottleneck list, severity ranking, business impact,
technical root cause, recommended fix, implementation priority,
revised architecture / service boundary map.

**Reject if:** bottlenecks generic, no ranking, root causes missing,
fixes vague, architecture criticized but not improved.

### Memory and Token Optimization Engineer
Must contain: tiered memory model, schema separation, deduplication rules,
pruning/archival policy, retrieval pipeline improvement, token budget logic,
summary integrity safeguards, measurable optimization metrics.

**Reject if:** memory vague, retrieval not improved, token reduction claimed
but undefined, summaries compressed without truthfulness safeguards.

### Docker and Multi-User Platform Engineer
Must contain: service boundary design, Dockerfiles/templates, docker-compose plan,
environment strategy, persistent storage strategy, user/session isolation plan,
health checks, scaling guidance, stateful vs stateless explanation.

**Reject if:** Docker superficial, services split without justification,
multi-user safety not addressed, stores not persisted, deployment not reproducible.

## Output Per Agent
```
verdict:  PASS | FAIL | NOT_RUN
missing:  list of required sections absent
weak:     list of insufficiently specific sections
drift:    scope drift detected
revisions: ordered list of required fixes
status:   Accepted | Rejected pending revision | Not run
```

## Report Outputs
| Artifact | Location |
|---|---|
| Markdown report | `output/specialist_validation_<timestamp>.md` |
| HTML report | `output/specialist_validation_<timestamp>.html` |

Both open in browser automatically.

## Static Fallback (no LLM)
Performs structural presence checks:
- File existence for each required artifact
- Keyword coverage (bottleneck, severity, volume, health check, etc.)
- Flags static-scan-only outputs from the Bottleneck Auditor

Static mode cannot catch contradiction, fluff, or missing *quality* — only missing structure.

## LLM Configuration (shared with other tool agents)
Uses `config.py` `AppConfig` for:
- `element_llm_gateway_url` or `element_llm_gateway_project_id`
- `element_llm_gateway_api_key`
- `element_llm_gateway_model` (default: `element:gpt-4o`)
- `wmt_ca_path` for TLS verification
