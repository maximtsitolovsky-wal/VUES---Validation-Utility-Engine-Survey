#!/usr/bin/env python3
"""Docker and Multi-User Platform Engineer — generates a Docker-first deployment
platform for SiteOwlQA, adapted to the actual stack and Windows-to-Linux constraints.

Scans the codebase, assembles stack evidence, calls the Element LLM Gateway for
a full platform design (same pydantic-ai pattern used project-wide), then writes
real Dockerfiles, docker-compose.yml, nginx config, start scripts, .env.example,
and infra/README.md to infra/.  Falls back to hardened static artifacts when the
LLM is not configured.

Usage:
    python tools/docker_platform_engineer.py
    python tools/docker_platform_engineer.py --no-llm
    python tools/docker_platform_engineer.py --no-browser
"""
from __future__ import annotations

import argparse
import html as _html
import os
import re
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_INFRA = _REPO / "infra"
_OUTPUT = _REPO / "output"

if str(_REPO / "src") not in sys.path:
    sys.path.insert(0, str(_REPO / "src"))

try:
    import httpx
    from openai import AsyncOpenAI
    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIModel
    from pydantic_ai.providers.openai import OpenAIProvider
    _LLM_DEPS = True
except ImportError:
    _LLM_DEPS = False


# ---------------------------------------------------------------------------
# Stack evidence scanner
# ---------------------------------------------------------------------------

def _scan_stack() -> dict:
    """Inspect the repo and return Docker-relevant facts as a plain dict."""
    src = _REPO / "src" / "siteowlqa"
    env_ex = _REPO / ".env.example"
    pyproject = _REPO / "pyproject.toml"
    req = _REPO / "requirements.txt"

    modules = [p.stem for p in sorted(src.glob("*.py")) if p.name != "__init__.py"]
    workers = [m for m in modules if "worker" in m]
    thread_modules = []
    volume_paths: set[str] = set()

    for p in src.glob("*.py"):
        try:
            src_text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "threading" in src_text:
            thread_modules.append(p.stem)
        for m in re.findall(r'["\']([A-Z_]+_DIR)["\']', src_text):
            volume_paths.add(m)

    env_vars: dict[str, str] = {}
    if env_ex.exists():
        for line in env_ex.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env_vars[k.strip()] = v.strip()

    deps: list[str] = []
    if req.exists():
        deps = [
            l.strip().split(">=")[0].split("==")[0]
            for l in req.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")
        ]

    correction_paths = {
        k: v for k, v in env_vars.items()
        if k.startswith("CORRECTION_") and v and "OneDrive" in v
    }

    return {
        "modules": modules,
        "workers": workers,
        "thread_modules": thread_modules,
        "dependencies": deps,
        "env_vars": env_vars,
        "dashboard_port": "8765",
        "dashboard_port_source": "output/dashboard.port (dynamic, preferred 8765)",
        "sql_auth": "Windows Trusted Connection (Trusted_Connection=yes) — NOT usable in Linux containers",
        "sql_auth_docker_fix": "Switch to SQL Server auth: add UID/PWD to connection string; mount config via volume",
        "correction_paths_onedrive": correction_paths,
        "external_services": ["Airtable REST API (cloud)", "SQL Server (external, Windows Auth)", "Element LLM Gateway (Walmart internal, optional)"],
        "persistent_dirs": ["archive/", "output/", "logs/", "temp/", "corrections/"],
        "correction_db": "SQLite (CorrectionStateDB) — naturally volume-mountable",
        "worker_model": f"{len(workers)} named worker threads + main poll thread (no separate processes)",
        "python_req": ">=3.11",
        "docker_installed": False,
        "os": "Windows 11",
    }


def _format_evidence(stack: dict) -> str:
    ev = [
        "## Discovered Stack Evidence",
        f"- Modules: {', '.join(stack['modules'])}",
        f"- Workers (named threads): {', '.join(stack['workers'])}",
        f"- Threading modules: {', '.join(stack['thread_modules'])}",
        f"- Dependencies: {', '.join(stack['dependencies'])}",
        f"- Dashboard port: {stack['dashboard_port_source']}",
        f"- SQL auth model: {stack['sql_auth']}",
        f"- Docker fix required: {stack['sql_auth_docker_fix']}",
        f"- External services: {', '.join(stack['external_services'])}",
        f"- Persistent directories: {', '.join(stack['persistent_dirs'])}",
        f"- Correction DB: {stack['correction_db']}",
        f"- Worker model: {stack['worker_model']}",
        f"- Python requirement: {stack['python_req']}",
        f"- Docker installed on host: {stack['docker_installed']} — platform design targets future deployment",
        "",
        "## Current env vars (.env.example)",
    ]
    for k, v in stack["env_vars"].items():
        ev.append(f"  {k}={v}")
    return "\n".join(ev)


# ---------------------------------------------------------------------------
# LLM design
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are Docker and Multi-User Platform Engineer.

Design and generate a Docker-first deployment architecture for this AI application
so multiple users can use it safely, reliably, and consistently across environments.

Critical constraint: the app currently uses Windows Trusted Connection for SQL Server.
Linux containers cannot use Windows Auth. Your design MUST switch to SQL Server
Authentication (UID/PWD) and document this clearly. The Dockerfile must install
Microsoft ODBC Driver 17 for SQL Server on Debian.

Required output (use exact markdown headings and code fences shown):

# Docker-First Deployment Architecture

## Executive Verdict
[Direct: single-user fragile / multi-user safe / under-isolated / over-split / production-credible]

## Services and Responsibilities
| Service | Why It Exists | Public? | Stateful? | Scales Horizontally? |
|---|---|---|---|---|
| ... |

## Stateful vs Stateless Map
- Stateless: ...
- Stateful: ...

## infra/Dockerfile
```dockerfile
# full multi-stage Dockerfile
```

## infra/docker-compose.yml
```yaml
# complete Compose with networks, volumes, health checks
```

## infra/docker-compose.override.yml
```yaml
# dev overrides: source mounts, direct port exposure
```

## infra/nginx/nginx.conf
```nginx
# reverse proxy: single public entrypoint on :80
```

## infra/.env.example
```dotenv
# grouped vars: pipeline, SQL auth, Airtable, LLM, paths
```

## infra/scripts/start.sh
```bash
#!/bin/bash
# container entrypoint
```

## infra/.dockerignore
```
# patterns to exclude from build context
```

## infra/README.md
```markdown
# infra deployment guide including SQL auth migration note
```

## Volume and Network Strategy
- Volumes: ...
- Networks: ...

## Health Check Plan
- pipeline: ...
- proxy: ...

## Multi-User Scaling Notes
- Isolation: ...
- Horizontal scaling: ...

## Local Development Workflow
1. ...

## Production Transition Guidance
- ...

## Common Mistakes to Avoid
- ...

Behavior rules:
- do not create a fake microservice zoo
- no separate service unless operationally justified
- SQL Server and Airtable stay external (not containerized)
- keep it clean, reproducible, and safe for multiple concurrent users
"""


def _build_llm_base_url(cfg: object) -> str:
    url = getattr(cfg, "element_llm_gateway_url", "")
    if url:
        return url
    pid = getattr(cfg, "element_llm_gateway_project_id", "")
    if pid:
        return f"https://ml.prod.walmart.com:31999/element/genai/project/{pid}/openai/v1"
    return ""


def _run_llm_design(stack: dict, cfg: object) -> str | None:
    if not _LLM_DEPS:
        print("[WARN] pydantic-ai/openai/httpx not installed — using static artifacts.")
        return None
    base_url = _build_llm_base_url(cfg)
    api_key = getattr(cfg, "element_llm_gateway_api_key", "")
    if not base_url or not api_key:
        print("[WARN] Element LLM Gateway not configured — using static artifacts.")
        return None

    ca = getattr(cfg, "wmt_ca_path", "") or os.getenv("WMT_CA_PATH", "") or True
    client = AsyncOpenAI(
        base_url=base_url,
        api_key="ignored",
        default_headers={"X-Api-Key": api_key},
        http_client=httpx.AsyncClient(verify=ca),
    )
    model_name = getattr(cfg, "element_llm_gateway_model", "") or "element:gpt-4o"
    model = OpenAIModel(model_name, provider=OpenAIProvider(openai_client=client))
    agent = Agent(model, instructions=_SYSTEM_PROMPT)

    prompt = (
        "Design a Docker-first deployment platform for this application. "
        "Use exact heading format from your instructions.\n\n"
        + _format_evidence(stack)
    )
    print(f"[INFO] Calling {model_name} for platform design ...")
    try:
        result = agent.run_sync(prompt)
        text = getattr(result, "output", None) or getattr(result, "data", None) or str(result)
        return str(text).strip() or None
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] LLM design failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Artifact extraction from LLM markdown output
# ---------------------------------------------------------------------------

_HEADING_TO_PATH: list[tuple[re.Pattern, str]] = [
    (re.compile(r"dockerignore", re.I),            ".dockerignore"),
    (re.compile(r"docker.compose.override", re.I), "docker-compose.override.yml"),
    (re.compile(r"docker.compose", re.I),          "docker-compose.yml"),
    (re.compile(r"nginx.*conf|nginx.*config", re.I), "nginx/nginx.conf"),
    (re.compile(r"\.env\.example", re.I),          ".env.example"),
    (re.compile(r"start\.sh", re.I),               "scripts/start.sh"),
    (re.compile(r"dockerfile", re.I),              "Dockerfile"),
    (re.compile(r"readme", re.I),                  "README.md"),
]


def _extract_artifacts(md: str) -> dict[str, str]:
    """Parse LLM markdown output and extract code blocks mapped to file paths."""
    artifacts: dict[str, str] = {}
    lines = md.splitlines()
    current_heading = ""
    in_block = False
    buf: list[str] = []

    for line in lines:
        if line.startswith("#"):
            current_heading = line.lstrip("#").strip()
        if line.startswith("```") and not in_block:
            in_block = True
            buf = []
            continue
        if line.startswith("```") and in_block:
            in_block = False
            content = "\n".join(buf).strip()
            if content:
                for pattern, rel_path in _HEADING_TO_PATH:
                    if pattern.search(current_heading):
                        artifacts[rel_path] = content
                        break
            buf = []
            continue
        if in_block:
            buf.append(line)

    return artifacts


# ---------------------------------------------------------------------------
# Static artifact fallback (hardened, production-correct defaults)
# ---------------------------------------------------------------------------

def _static_artifacts() -> dict[str, str]:
    return {
        "Dockerfile": """\
# syntax=docker/dockerfile:1
# SiteOwlQA — Pipeline + Dashboard Server
# NOTE: Windows Trusted Connection cannot be used in Linux containers.
#       Set DB_USE_SQL_AUTH=true and provide DB_USER / DB_PASSWORD in .env.
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \\
    PYTHONIOENCODING=utf-8 \\
    DEBIAN_FRONTEND=noninteractive

# Microsoft ODBC Driver 17 for SQL Server (required by pyodbc)
RUN apt-get update && apt-get install -y --no-install-recommends \\
        curl gnupg2 ca-certificates unixodbc-dev && \\
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \\
      | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg && \\
    echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] \\
      https://packages.microsoft.com/debian/12/prod bookworm main" \\
      > /etc/apt/sources.list.d/mssql-release.list && \\
    apt-get update && \\
    ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 && \\
    apt-get purge -y curl gnupg2 && \\
    rm -rf /var/lib/apt/lists/*

# --- dependency layer (cached unless requirements.txt changes) ---
FROM base AS deps
WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir -r requirements.txt

# --- runtime image ---
FROM base AS runtime
WORKDIR /app

# Copy installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Non-root user
RUN useradd -m -u 1001 -s /bin/bash siteowl

# App source (no .venv, no logs, no output — see .dockerignore)
COPY --chown=siteowl:siteowl . .

# Runtime directories (volumes will overlay these in compose)
RUN mkdir -p output logs temp archive corrections && \\
    chown -R siteowl:siteowl output logs temp archive corrections

USER siteowl

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \\
  CMD curl -sf http://localhost:8765/executive_dashboard.html || exit 1

ENTRYPOINT ["infra/scripts/start.sh"]
""",
        "docker-compose.yml": """\
# SiteOwlQA — Docker Compose (production-like)
# SQL Server and Airtable are external services — not containerized.
# Override with docker-compose.override.yml for local development.
version: "3.9"

services:
  pipeline:
    build:
      context: ..
      dockerfile: infra/Dockerfile
      target: runtime
    image: siteowlqa:latest
    restart: unless-stopped
    env_file: .env
    volumes:
      - archive_data:/app/archive
      - output_data:/app/output
      - logs_data:/app/logs
      - corrections_data:/app/corrections
      # temp is ephemeral — no named volume needed
    networks:
      - backend
    expose:
      - "8765"
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8765/executive_dashboard.html || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 90s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"

  proxy:
    image: nginx:1.27-alpine
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      pipeline:
        condition: service_healthy
    networks:
      - edge
      - backend
    healthcheck:
      test: ["CMD-SHELL", "nginx -t 2>/dev/null && curl -sf http://localhost/health || exit 1"]
      interval: 20s
      timeout: 5s
      retries: 3

volumes:
  archive_data:
    driver: local
  output_data:
    driver: local
  logs_data:
    driver: local
  corrections_data:
    driver: local

networks:
  edge:
    name: siteowlqa_edge
  backend:
    name: siteowlqa_backend
    internal: true
""",
        "docker-compose.override.yml": """\
# Local development overrides — NOT for production.
# Mounts source code for hot-reload and exposes pipeline port directly.
version: "3.9"

services:
  pipeline:
    build:
      target: runtime
    volumes:
      # Live source mount — changes take effect on restart
      - ../src:/app/src:ro
      - ../main.py:/app/main.py:ro
      - ../tools:/app/tools:ro
      - ../prompts:/app/prompts:ro
    ports:
      # Expose pipeline dashboard directly for dev debugging
      - "8765:8765"
    environment:
      POLL_INTERVAL_SECONDS: "30"

  proxy:
    ports:
      # Use 8080 in dev to avoid conflicts with system port 80
      - "8080:80"
""",
        "nginx/nginx.conf": """\
# SiteOwlQA — Nginx reverse proxy
# Single public entrypoint. Pipeline stays on private backend network.
events {
    worker_connections 1024;
}

http {
    upstream pipeline {
        server pipeline:8765;
        keepalive 16;
    }

    log_format main '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent"';

    access_log /var/log/nginx/access.log main;
    error_log  /var/log/nginx/error.log warn;

    server {
        listen 80;
        server_name _;

        # Lightweight health check (does not hit pipeline)
        location = /health {
            return 200 "ok\\n";
            add_header Content-Type text/plain;
        }

        location / {
            proxy_pass         http://pipeline;
            proxy_http_version 1.1;
            proxy_set_header   Connection        "";
            proxy_set_header   Host              $host;
            proxy_set_header   X-Real-IP         $remote_addr;
            proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
            proxy_set_header   X-Forwarded-Proto $scheme;
            proxy_read_timeout 60s;

            # Dashboard must never be stale — match pipeline server headers
            add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0";
            add_header Pragma       "no-cache";
        }
    }
}
""",
        ".env.example": """\
# =====================================================================
# SiteOwlQA — Docker Environment Template
# Copy to .env, fill in real values.  Never commit .env.
# =====================================================================

# --- Pipeline behaviour -----------------------------------------------
POLL_INTERVAL_SECONDS=60
WORKER_THREADS=3
REFERENCE_SOURCE=sql
CORRECTION_POLL_INTERVAL_SECONDS=300

# --- Container-internal paths (match docker-compose.yml volumes) ------
TEMP_DIR=/app/temp
OUTPUT_DIR=/app/output
LOG_DIR=/app/logs
ARCHIVE_DIR=/app/archive
SUBMISSIONS_DIR=/app/archive/submissions
CORRECTION_LOG_DIR=/app/corrections

# --- SQL Server (SQL Auth — Windows Trusted Auth is unavailable in Linux)
# Use 'host.docker.internal' to reach SQL Server on the Docker host machine.
SQL_SERVER=host.docker.internal
SQL_DATABASE=SiteOwlQA
SQL_DRIVER=ODBC Driver 17 for SQL Server
# SQL auth credentials (added for Docker; see infra/README.md)
DB_USER=siteowlqa_svc
DB_PASSWORD=change-me

# --- Airtable --------------------------------------------------------
AIRTABLE_TOKEN=
AIRTABLE_BASE_ID=
AIRTABLE_TABLE_NAME=

# --- Element LLM Gateway (optional) ----------------------------------
ELEMENT_LLM_GATEWAY_URL=
ELEMENT_LLM_GATEWAY_API_KEY=
ELEMENT_LLM_GATEWAY_MODEL=element:gpt-4o
ELEMENT_LLM_GATEWAY_PROJECT_ID=
WMT_CA_PATH=
""",
        "scripts/start.sh": """\
#!/bin/bash
# SiteOwlQA container entrypoint
set -euo pipefail

echo "[start] SiteOwlQA pipeline starting in container..."
echo "[start] Python: $(python --version)"
echo "[start] Working dir: $(pwd)"

# Ensure volume-mounted dirs exist (fresh volumes are empty)
mkdir -p /app/output /app/logs /app/temp /app/archive /app/corrections

# Validate required env vars before starting
: "${AIRTABLE_TOKEN:?AIRTABLE_TOKEN is required}"
: "${AIRTABLE_BASE_ID:?AIRTABLE_BASE_ID is required}"
: "${SQL_SERVER:?SQL_SERVER is required}"
: "${SQL_DATABASE:?SQL_DATABASE is required}"

echo "[start] Config validated. Launching pipeline..."
exec python -u main.py
""",
        ".dockerignore": """\
# Build context exclusions — keeps image lean and secrets out
.venv/
venv/
__pycache__/
*.pyc
*.pyo
.env
.git/
.gitignore
*.log
logs/
output/
temp/
archive/
share/
served_dashboard/
*.sqlite
*.db
*.csv
*.xlsx
*.xls
SiteOwlQA.exe
node_modules/
docs/
legacy_db_tools/
skills/
MEMORY.md
CLAUDE.md
""",
        "README.md": """\
# SiteOwlQA — Infra & Docker Deployment Guide

## Prerequisites
- Docker Engine 24+ and Docker Compose v2
- SQL Server accessible from the Docker host (not containerized)
- Airtable API token with `data.records:read` + `data.records:write`

---

## Quick Start (local / dev)

```bash
# 1. Copy and fill in secrets
cp infra/.env.example infra/.env
# Edit infra/.env — see SQL Auth note below

# 2. Build and start
cd infra
docker compose -f docker-compose.yml -f docker-compose.override.yml up --build

# 3. Open dashboard
open http://localhost:8080   # via proxy
open http://localhost:8765   # direct (dev override only)
```

---

## ⚠️ SQL Server Auth Migration Required

The application currently uses **Windows Trusted Connection**
(`Trusted_Connection=yes`) which does not work in Linux containers.

### What to change in `src/siteowlqa/config.py`

```python
# BEFORE (Windows Auth — works on bare metal, not in Docker)
@property
def sql_connection_string(self) -> str:
    return (
        f"DRIVER={{{self.sql_driver}}};"
        f"SERVER={self.sql_server};"
        f"DATABASE={self.sql_database};"
        "Trusted_Connection=yes;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )

# AFTER (SQL Auth — works everywhere including Docker)
@property
def sql_connection_string(self) -> str:
    uid = os.getenv("DB_USER", "")
    pwd = os.getenv("DB_PASSWORD", "")
    auth = (
        f"UID={uid};PWD={pwd};"
        if uid else
        "Trusted_Connection=yes;"
    )
    return (
        f"DRIVER={{{self.sql_driver}}};"
        f"SERVER={self.sql_server};"
        f"DATABASE={self.sql_database};"
        + auth +
        "Encrypt=yes;TrustServerCertificate=yes;"
    )
```

Set `DB_USER` and `DB_PASSWORD` in `infra/.env`.
Leave them blank to keep Windows Auth for bare-metal installs.

### SQL Server: create a login for the container service account

```sql
CREATE LOGIN siteowlqa_svc WITH PASSWORD = 'strong-password-here';
USE SiteOwlQA;
CREATE USER siteowlqa_svc FOR LOGIN siteowlqa_svc;
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::dbo TO siteowlqa_svc;
```

---

## Reaching SQL Server from Docker

If SQL Server runs on the Docker host machine, use:
```
SQL_SERVER=host.docker.internal
```
`host.docker.internal` resolves to the host IP on Docker Desktop (Windows/Mac)
and requires `--add-host=host.docker.internal:host-gateway` on Linux Engine.

---

## Services

| Service  | Port (public) | Network          | Stateful? |
|----------|---------------|------------------|-----------|
| proxy    | 80            | edge + backend   | No        |
| pipeline | 8765 (internal) | backend only   | No (volumes) |

All data lives in **named volumes** — pipeline container is stateless.

---

## Volumes

| Volume           | Mounted at          | Contains                     |
|-----------------|---------------------|------------------------------|
| archive_data     | /app/archive        | Submission JSON + raw files  |
| output_data      | /app/output         | CSV + HTML dashboards        |
| logs_data        | /app/logs           | Rotating pipeline logs       |
| corrections_data | /app/corrections    | SQLite CorrectionStateDB     |

---

## Production Checklist

- [ ] Move `infra/.env` secrets into a real secret manager (Vault, AWS SSM, etc.)
- [ ] Pin Docker image tags to immutable versions
- [ ] Enable TLS on nginx (certbot or managed load balancer)
- [ ] Set up log aggregation (ELK, Datadog, etc.)
- [ ] Schedule volume backups for `archive_data` and `corrections_data`
- [ ] Run `docker compose up -d` under systemd or a container orchestrator
- [ ] Test `host.docker.internal` SQL connectivity before go-live

---

## Scaling Notes

**pipeline** can run multiple replicas IF:
1. The SQL Auth migration is done (shared SQL state, not local Windows Auth)
2. `output/dashboard.port` file races are accepted or moved to a shared volume
3. Correction SQLite is replaced with a proper DB (SQLite is single-writer)

**proxy** (nginx) is stateless — scale freely.

**Do NOT** containerize SQL Server unless you own its HA and backup strategy.
""",
    }


# ---------------------------------------------------------------------------
# File writer
# ---------------------------------------------------------------------------

def _write_artifacts(artifacts: dict[str, str]) -> list[Path]:
    written: list[Path] = []
    for rel, content in artifacts.items():
        dest = _INFRA / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        # Make shell scripts executable (best-effort on Windows)
        if rel.endswith(".sh"):
            try:
                dest.chmod(0o755)
            except OSError:
                pass
        written.append(dest)
        print(f"[write] {dest.relative_to(_REPO)}")
    return written


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

def _report_html(stack: dict, written: list[Path], stamp: str) -> str:
    file_rows = "".join(
        f"<tr><td><code>{_html.escape(str(p.relative_to(_REPO)))}</code></td>"
        f"<td>{p.stat().st_size:,} bytes</td></tr>"
        for p in written
    )
    ext_rows = "".join(
        f"<tr><td>{_html.escape(s)}</td></tr>" for s in stack["external_services"]
    )
    vol_rows = "".join(
        f"<tr><td>{_html.escape(v)}</td></tr>" for v in stack["persistent_dirs"]
    )
    css = ("body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;"
           "padding:0 1.5rem;color:#1a1a1a;line-height:1.6}"
           "h1,h2{color:#0053e2} h2{margin-top:2rem;border-bottom:2px solid #e5e7f0;padding-bottom:.3rem}"
           "table{width:100%;border-collapse:collapse;margin:.75rem 0;font-size:.87rem}"
           "th{background:#0053e2;color:#fff;padding:.4rem .65rem;text-align:left}"
           "td{padding:.35rem .65rem;border-bottom:1px solid #e5e7f0}"
           "tr:nth-child(even) td{background:#f5f8ff}"
           "code{background:#f0f0f0;padding:.1rem .3rem;border-radius:3px;font-size:.82rem}"
           ".warn{background:#fffbf0;border-left:4px solid #ffc220;padding:.75rem 1rem;border-radius:0 6px 6px 0;margin:1rem 0}"
           ".ok{background:#f0faf0;border-left:4px solid #2a8703;padding:.75rem 1rem;border-radius:0 6px 6px 0;margin:1rem 0}"
           ".banner{background:#0053e2;color:#fff;padding:1.25rem 1.5rem;border-radius:10px;margin-bottom:1.75rem}"
           ".banner h1{color:#fff;margin:0;font-size:1.45rem;border:none}"
           ".banner p{margin:.25rem 0 0;opacity:.8;font-size:.87rem}")
    return (
        f"<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>"
        f"<title>Docker Platform Design — SiteOwlQA</title><style>{css}</style></head><body>"
        f"<div class='banner'><h1>&#128679; Docker &amp; Multi-User Platform Engineer</h1>"
        f"<p>Generated: {_html.escape(stamp)} &nbsp;|&nbsp; SiteOwlQA Pipeline</p></div>"
        f"<div class='warn'>&#9888; <strong>SQL Server Windows Auth is not usable in Linux containers.</strong>"
        f" See <code>infra/README.md</code> for the SQL auth migration and the one-property fix in config.py.</div>"
        f"<div class='ok'>&#10003; <strong>{len(written)} artifact(s) written to <code>infra/</code>.</strong>"
        f" Run <code>cd infra &amp;&amp; docker compose up --build</code> after completing the SQL auth step.</div>"
        f"<h2>Generated Files</h2><table><tr><th>Path</th><th>Size</th></tr>{file_rows}</table>"
        f"<h2>External Services (not containerized)</h2>"
        f"<table><tr><th>Service</th></tr>{ext_rows}</table>"
        f"<h2>Named Volumes</h2><table><tr><th>Directory</th></tr>{vol_rows}</table>"
        f"<h2>Next Steps</h2><ol>"
        f"<li>Apply the SQL auth change to <code>src/siteowlqa/config.py</code> — see <code>infra/README.md</code></li>"
        f"<li>Create a SQL Server login for the service account</li>"
        f"<li>Copy <code>infra/.env.example</code> → <code>infra/.env</code> and fill in secrets</li>"
        f"<li><code>cd infra &amp;&amp; docker compose -f docker-compose.yml -f docker-compose.override.yml up --build</code></li>"
        f"<li>Install Docker: <code>winget install Docker.DockerDesktop</code></li>"
        f"</ol></body></html>"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM call, write static artifacts only")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser when done")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("[INFO] Scanning stack ...")
    stack = _scan_stack()
    print(f"[INFO] Found {len(stack['modules'])} modules, {len(stack['workers'])} worker types")
    print(f"[INFO] SQL auth model: {stack['sql_auth']}")

    artifacts: dict[str, str] = {}

    if not args.no_llm:
        cfg = None
        try:
            from siteowlqa.config import load_config  # noqa: PLC0415
            cfg = load_config()
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] Could not load app config ({exc}) — using static artifacts.")

        if cfg is not None:
            llm_md = _run_llm_design(stack, cfg)
            if llm_md:
                artifacts = _extract_artifacts(llm_md)
                print(f"[INFO] LLM produced {len(artifacts)} parseable artifact(s).")

    # Fill any missing artifacts with static fallback
    static = _static_artifacts()
    before = len(artifacts)
    for rel, content in static.items():
        artifacts.setdefault(rel, content)
    if len(artifacts) > before:
        print(f"[INFO] Static fallback filled {len(artifacts) - before} artifact(s).")

    print(f"[INFO] Writing {len(artifacts)} file(s) to infra/ ...")
    written = _write_artifacts(artifacts)

    _OUTPUT.mkdir(parents=True, exist_ok=True)
    report_path = _OUTPUT / f"docker_platform_{stamp}.html"
    report_path.write_text(_report_html(stack, written, stamp), encoding="utf-8")
    print(f"[OK] Report: {report_path}")

    if not args.no_browser:
        webbrowser.open(report_path.as_uri())
        print("[OK] Opened in browser.")


if __name__ == "__main__":
    main()
