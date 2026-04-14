# Agent: docker-platform-engineer
**Category:** Tool Agent  
**Type:** pydantic-ai `Agent` instance (run-on-demand)  
**LLM:** `element:gpt-4o` via Walmart Element LLM Gateway  
**CLI Tool:** `tools/docker_platform_engineer.py`  
**LLM Agent:** ✅ Yes — `Agent(model, instructions=_SYSTEM_PROMPT)` called in `_run_llm_design()`

---

## What It Is
A pydantic-ai `Agent` that designs and generates a full Docker-first deployment
platform for SiteOwlQA. Run on demand — not part of the submission pipeline.

When the LLM is available, it scans the codebase, assembles stack evidence, calls
the Element Gateway for a full platform design, then writes real Dockerfiles,
`docker-compose.yml`, nginx config, start scripts, `.env.example`, and `infra/README.md`
to `infra/`. Falls back to hardened static artifacts when LLM is not configured.

## Usage
```bash
python tools/docker_platform_engineer.py             # LLM + browser
python tools/docker_platform_engineer.py --no-llm    # static artifacts only
python tools/docker_platform_engineer.py --no-browser
```

## What It Generates → `infra/`
| File | Purpose |
|---|---|
| `Dockerfile` | Multi-stage build with ODBC Driver 17 for SQL Server on Debian |
| `docker-compose.yml` | Production Compose — named volumes, health checks, internal backend network |
| `docker-compose.override.yml` | Dev overrides — source mounts, direct port exposure |
| `nginx/nginx.conf` | Reverse proxy — single public entrypoint on `:80` |
| `.env.example` | Grouped env vars: pipeline, SQL auth, Airtable, LLM, paths |
| `scripts/start.sh` | Container entrypoint — validates required env vars before start |
| `.dockerignore` | Excludes venv, logs, output, archive, secrets |
| `README.md` | Deployment guide including SQL auth migration step |

## Critical Constraint It Always Flags
> **Windows Trusted Connection (`Trusted_Connection=yes`) is not usable in Linux containers.**
> The agent designs for SQL Server Authentication (UID/PWD) and documents the one-property
> fix required in `src/siteowlqa/config.py`.

## LLM System Prompt Role
```
You are Docker and Multi-User Platform Engineer.
Design and generate a Docker-first deployment architecture for this AI application
so multiple users can use it safely, reliably, and consistently across environments.
```

## Stack Evidence It Scans
- Python modules in `src/siteowlqa/`
- Named worker threads detected by source inspection
- Dependencies from `requirements.txt`
- env vars from `.env.example`
- Dashboard port from `output/dashboard.port`
- External services: Airtable, SQL Server, Element LLM Gateway
- Persistent directories: `archive/`, `output/`, `logs/`, `temp/`, `corrections/`

## Outputs an HTML Report
`output/docker_platform_<timestamp>.html` — opens in browser automatically.

## LLM Configuration (shared with element-llm-gateway)
Uses `config.py` `AppConfig` for:
- `element_llm_gateway_url` or `element_llm_gateway_project_id`
- `element_llm_gateway_api_key`
- `element_llm_gateway_model` (default: `element:gpt-4o`)
- `wmt_ca_path` for TLS verification
