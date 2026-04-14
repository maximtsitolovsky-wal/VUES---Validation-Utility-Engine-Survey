# Agent: system-bottleneck-auditor
**Category:** Tool Agent  
**Type:** pydantic-ai `Agent` instance (run-on-demand)  
**LLM:** `element:gpt-4o` via Walmart Element LLM Gateway  
**CLI Tool:** `tools/system_bottleneck_auditor.py`  
**LLM Agent:** ✅ Yes — `Agent(model, instructions=_SYSTEM_PROMPT)` called in `_run_llm_audit()`

---

## What It Is
A pydantic-ai `Agent` that audits SiteOwlQA's architecture for bottlenecks.
Run on demand — not part of the submission pipeline.

Scans the codebase via AST inspection, assembles structured system evidence
(modules, threading, data stores, integrations, key facts), then calls the
Element Gateway for a ruthless bottleneck audit. Falls back to a static
structural scan when LLM is not configured.

## Usage
```bash
python tools/system_bottleneck_auditor.py             # LLM + browser
python tools/system_bottleneck_auditor.py --no-llm   # static scan only
python tools/system_bottleneck_auditor.py --no-browser
```

## LLM System Prompt Role
```
You are System Bottleneck Auditor.
Audit the provided AI application architecture.
Be ruthless; do not preserve weak architecture for convenience.
Treat every component as guilty until justified.
```

## What It Audits
| Area | What It Inspects |
|---|---|
| Module inventory | Lines, threading, queues, SQL, Airtable, HTTP, worker flags |
| Data stores | SQL Server, filesystem, SQLite, in-process SubmissionQueue |
| External integrations | Airtable API, Element LLM Gateway, localhost dashboard server |
| Runtime configuration | All vars from `.env.example` |
| Architecture facts | Concurrency model, worker design, crash recovery, email delegation |

## Evidence It Collects (AST-based)
- Module line counts, docstrings
- `threading` usage detected per module
- `Queue` / `SubmissionQueue` usage detected per module
- SQL (`pyodbc`) usage detected per module
- Airtable API usage detected per module
- HTTP client usage (`requests`, `httpx`, `urlopen`) detected per module
- Worker modules identified by name and source pattern

## Report Output Format (from LLM)
```
# Architecture Bottleneck Audit
## Executive Verdict
## Bottleneck Summary (table)
## Detailed Findings (per bottleneck)
## Synchronous vs Asynchronous Split
## Scaling and Concurrency Risks
## Reliability and Operational Risks
## Revised High-Level Architecture
## Cleaner Service Boundary Map
## Priority-Ordered Remediation Plan
```

## Outputs
| Artifact | Location |
|---|---|
| Markdown report | `output/bottleneck_audit_<timestamp>.md` |
| HTML report | `output/bottleneck_audit_<timestamp>.html` |

Both open in browser automatically.

## LLM Configuration (shared with element-llm-gateway)
Uses `config.py` `AppConfig` for:
- `element_llm_gateway_url` or `element_llm_gateway_project_id`
- `element_llm_gateway_api_key`
- `element_llm_gateway_model` (default: `element:gpt-4o`)
- `wmt_ca_path` for TLS verification

## Related Audit: bat Launcher
```
ops/windows/run_bottleneck_audit.bat
```
Convenience launcher that sets up the env and runs the auditor from Windows.
