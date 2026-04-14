# SiteOwlQA — Infra & Docker Deployment Guide

## Service Boundary Design

Two services. One public entrypoint. Internal services never exposed.

| Service  | Role                                    | Network(s)     | Public Port           |
|----------|-----------------------------------------|----------------|-----------------------|
| proxy    | Reverse proxy — single public entrypoint | edge + backend | 80                    |
| pipeline | Python pipeline + dashboard server      | backend only   | none (internal :8765) |

### Network Topology
- `edge`: proxy only. Accepts traffic from the outside world.
- `backend` (`internal: true`): pipeline + proxy internal leg. No host port exposure.
- SQL Server, Airtable, and Element LLM Gateway are **external** — not containerised.

### Boundary Decisions
- `pipeline` co-locates API and dashboard: no operational reason to split.
- No `db` container: SQL Server is managed externally.
- No `cache` container: no shared session or rate-limit state; single-process pipeline.
- No `worker` container: workers are daemon threads inside `pipeline` (same runtime).
- `proxy` is separate: different failure domain, owns the public interface.

---

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
