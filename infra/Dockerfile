# syntax=docker/dockerfile:1
# SiteOwlQA — Pipeline + Dashboard Server
# NOTE: Windows Trusted Connection cannot be used in Linux containers.
#       Set DB_USE_SQL_AUTH=true and provide DB_USER / DB_PASSWORD in .env.
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    DEBIAN_FRONTEND=noninteractive

# Microsoft ODBC Driver 17 for SQL Server (required by pyodbc)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg2 ca-certificates unixodbc-dev && \
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
      | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg && \
    echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] \
      https://packages.microsoft.com/debian/12/prod bookworm main" \
      > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 && \
    apt-get purge -y curl gnupg2 && \
    rm -rf /var/lib/apt/lists/*

# --- dependency layer (cached unless requirements.txt changes) ---
FROM base AS deps
WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
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
RUN mkdir -p output logs temp archive corrections && \
    chown -R siteowl:siteowl output logs temp archive corrections

USER siteowl

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
  CMD curl -sf http://localhost:8765/executive_dashboard.html || exit 1

ENTRYPOINT ["infra/scripts/start.sh"]
